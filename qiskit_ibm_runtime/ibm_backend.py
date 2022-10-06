# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Module for interfacing with an IBM Quantum Backend."""

import logging

from typing import Iterable, Union, Optional, Any, List
from datetime import datetime as python_datetime

from qiskit.qobj.utils import MeasLevel, MeasReturnType
from qiskit.providers.backend import BackendV2 as Backend
from qiskit.providers.options import Options
from qiskit.providers.models import (
    BackendStatus,
    BackendProperties,
    PulseDefaults,
    GateConfig,
    QasmBackendConfiguration,
    PulseBackendConfiguration,
)
from qiskit.pulse.channels import (
    AcquireChannel,
    ControlChannel,
    DriveChannel,
    MeasureChannel,
)
from qiskit.transpiler.target import Target

from qiskit_ibm_runtime import (  # pylint: disable=unused-import,cyclic-import
    qiskit_runtime_service,
)

from .api.clients import AccountClient, RuntimeClient
from .api.clients.backend import BaseBackendClient
from .exceptions import IBMBackendApiProtocolError
from .utils.backend_converter import (
    convert_to_target,
)
from .utils.converters import local_to_utc
from .utils.backend_decoder import (
    defaults_from_server_data,
    properties_from_server_data,
)

logger = logging.getLogger(__name__)


class IBMBackend(Backend):
    """Backend class interfacing with an IBM Quantum backend.

    Note:

        * You should not instantiate the ``IBMBackend`` class directly. Instead, use
          the methods provided by an :class:`QiskitRuntimeService` instance to retrieve and handle
          backends.

    This class represents an IBM Quantum backend. Its attributes and methods provide
    information about the backend. For example, the :meth:`status()` method
    returns a :class:`BackendStatus<qiskit.providers.models.BackendStatus>` instance.
    The instance contains the ``operational`` and ``pending_jobs`` attributes, which state whether
    the backend is operational and also the number of jobs in the server queue for the backend,
    respectively::

        status = backend.status()
        is_operational = status.operational
        jobs_in_queue = status.pending_jobs

    Here is list of attributes available on the ``IBMBackend`` class:

        * name: backend name.
        * backend_version: backend version in the form X.Y.Z.
        * num_qubits: number of qubits.
        * target: A :class:`qiskit.transpiler.Target` object for the backend.
        * basis_gates: list of basis gates names on the backend.
        * gates: list of basis gates on the backend.
        * local: backend is local or remote.
        * simulator: backend is a simulator.
        * conditional: backend supports conditional operations.
        * open_pulse: backend supports open pulse.
        * memory: backend supports memory.
        * max_shots: maximum number of shots supported.
        * coupling_map (list): The coupling map for the device
        * supported_instructions (List[str]): Instructions supported by the backend.
        * dynamic_reprate_enabled (bool): whether delay between programs can be set dynamically
          (ie via ``rep_delay``). Defaults to False.
        * rep_delay_range (List[float]): 2d list defining supported range of repetition
          delays for backend in μs. First entry is lower end of the range, second entry is
          higher end of the range. Optional, but will be specified when
          ``dynamic_reprate_enabled=True``.
        * default_rep_delay (float): Value of ``rep_delay`` if not specified by user and
          ``dynamic_reprate_enabled=True``.
        * n_uchannels: Number of u-channels.
        * u_channel_lo: U-channel relationship on device los.
        * meas_levels: Supported measurement levels.
        * qubit_lo_range: Qubit lo ranges for each qubit with form (min, max) in GHz.
        * meas_lo_range: Measurement lo ranges for each qubit with form (min, max) in GHz.
        * dt: Qubit drive channel timestep in nanoseconds.
        * dtm: Measurement drive channel timestep in nanoseconds.
        * rep_times: Supported repetition times (program execution time) for backend in μs.
        * meas_kernels: Supported measurement kernels.
        * discriminators: Supported discriminators.
        * hamiltonian: An optional dictionary with fields characterizing the system hamiltonian.
        * channel_bandwidth (list): Bandwidth of all channels
          (qubit, measurement, and U)
        * acquisition_latency (list): Array of dimension
          n_qubits x n_registers. Latency (in units of dt) to write a
          measurement result from qubit n into register slot m.
        * conditional_latency (list): Array of dimension n_channels
          [d->u->m] x n_registers. Latency (in units of dt) to do a
          conditional operation on channel n from register slot m
        * meas_map (list): Grouping of measurement which are multiplexed
        * max_circuits (int): The maximum number of experiments per job
        * sample_name (str): Sample name for the backend
        * n_registers (int): Number of register slots available for feedback
          (if conditional is True)
        * register_map (list): An array of dimension n_qubits X
          n_registers that specifies whether a qubit can store a
          measurement in a certain register slot.
        * configurable (bool): True if the backend is configurable, if the
          backend is a simulator
        * credits_required (bool): True if backend requires credits to run a
          job.
        * online_date (datetime): The date that the device went online
        * display_name (str): Alternate name field for the backend
        * description (str): A description for the backend
        * tags (list): A list of string tags to describe the backend
        * version: version of ``Backend`` class (Ex: 1, 2)
        * channels: An optional dictionary containing information of each channel -- their
          purpose, type, and qubits operated on.
        * parametric_pulses (list): A list of pulse shapes which are supported on the backend.
          For example: ``['gaussian', 'constant']``
        * processor_type (dict): Processor type for this backend. A dictionary of the
          form ``{"family": <str>, "revision": <str>, segment: <str>}`` such as
          ``{"family": "Canary", "revision": "1.0", segment: "A"}``.

            * family: Processor family of this backend.
            * revision: Revision version of this processor.
            * segment: Segment this processor belongs to within a larger chip.
    """

    id_warning_issued = False

    def __init__(
        self,
        configuration: Union[QasmBackendConfiguration, PulseBackendConfiguration],
        service: "qiskit_runtime_service.QiskitRuntimeService",
        api_client: BaseBackendClient,
    ) -> None:
        """IBMBackend constructor.

        Args:
            configuration: Backend configuration.
            service: Instance of QiskitRuntimeService.
            api_client: IBM client used to communicate with the server.
        """
        super().__init__(
            name=configuration.backend_name,
            online_date=configuration.online_date,
            backend_version=configuration.backend_version,
        )
        self._service = service
        self._api_client = api_client
        self._configuration = configuration
        self._properties = None
        self._defaults = None
        self._target = None
        self._max_circuits = configuration.max_experiments
        if not self._configuration.simulator:
            self.options.set_validator("noise_model", type(None))
            self.options.set_validator("seed_simulator", type(None))
        if hasattr(configuration, "max_shots"):
            self.options.set_validator("shots", (1, configuration.max_shots))
        if hasattr(configuration, "rep_delay_range"):
            self.options.set_validator(
                "rep_delay",
                (configuration.rep_delay_range[0], configuration.rep_delay_range[1]),
            )

    def __getattr__(self, name: str) -> Any:
        """Gets attribute from self or configuration

        This magic method executes when user accesses an attribute that
        does not yet exist on IBMBackend class.
        """
        # Lazy load properties and pulse defaults and construct the target object.
        self._get_properties()
        self._get_defaults()
        self._convert_to_target()
        # Check if the attribute now is available on IBMBackend class due to above steps
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        # If attribute is still not available on IBMBackend class,
        # fallback to check if the attribute is available in configuration
        try:
            return self._configuration.__getattribute__(name)
        except AttributeError:
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(
                    self.__class__.__name__, name
                )
            )

    def _get_properties(self) -> None:
        """Gets backend properties and decodes it"""
        if not self._properties:
            api_properties = self._api_client.backend_properties(self.name)
            if api_properties:
                backend_properties = properties_from_server_data(api_properties)
                self._properties = backend_properties

    def _get_defaults(self) -> None:
        """Gets defaults if pulse backend and decodes it"""
        if not self._defaults and isinstance(
            self._configuration, PulseBackendConfiguration
        ):
            api_defaults = self._api_client.backend_pulse_defaults(self.name)
            if api_defaults:
                self._defaults = defaults_from_server_data(api_defaults)

    def _convert_to_target(self) -> None:
        """Converts backend configuration, properties and defaults to Target object"""
        if not self._target:
            self._target = convert_to_target(
                configuration=self._configuration,
                properties=self._properties,
                defaults=self._defaults,
            )

    @classmethod
    def _default_options(cls) -> Options:
        """Default runtime options."""
        return Options(
            shots=4000,
            memory=False,
            qubit_lo_freq=None,
            meas_lo_freq=None,
            schedule_los=None,
            meas_level=MeasLevel.CLASSIFIED,
            meas_return=MeasReturnType.AVERAGE,
            memory_slots=None,
            memory_slot_size=100,
            rep_time=None,
            rep_delay=None,
            init_qubits=True,
            use_measure_esp=None,
            # Simulator only
            noise_model=None,
            seed_simulator=None,
        )

    @property
    def service(self) -> "qiskit_runtime_service.QiskitRuntimeService":
        """Return the ``service`` object

        Returns:
            service: instance of QiskitRuntimeService
        """
        return self._service

    @property
    def dtm(self) -> float:
        """Return the system time resolution of output signals

        Returns:
            dtm: The output signal timestep in seconds.
        """
        return self._configuration.dtm

    @property
    def max_circuits(self) -> int:
        """The maximum number of circuits

        The maximum number of circuits (or Pulse schedules) that can be
        run in a single job. If there is no limit this will return None.
        """
        return self._max_circuits

    @property
    def meas_map(self) -> List[List[int]]:
        """Return the grouping of measurements which are multiplexed

        This is required to be implemented if the backend supports Pulse
        scheduling.

        Returns:
            meas_map: The grouping of measurements which are multiplexed
        """
        return self._configuration.meas_map

    @property
    def target(self) -> Target:
        """A :class:`qiskit.transpiler.Target` object for the backend.

        Returns:
            Target
        """
        self._get_properties()
        self._get_defaults()
        self._convert_to_target()
        return self._target

    def properties(
        self, refresh: bool = False, datetime: Optional[python_datetime] = None
    ) -> Optional[BackendProperties]:
        """Return the backend properties, subject to optional filtering.

        This data describes qubits properties (such as T1 and T2),
        gates properties (such as gate length and error), and other general
        properties of the backend.

        The schema for backend properties can be found in
        `Qiskit/ibm-quantum-schemas
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/backend_properties_schema.json>`_.

        Args:
            refresh: If ``True``, re-query the server for the backend properties.
                Otherwise, return a cached version.
            datetime: By specifying `datetime`, this function returns an instance
                of the :class:`BackendProperties<qiskit.providers.models.BackendProperties>`
                whose timestamp is closest to, but older than, the specified `datetime`.
                Note that this is only supported using ``ibm_quantum`` runtime.

        Returns:
            The backend properties or ``None`` if the backend properties are not
            currently available.

        Raises:
            TypeError: If an input argument is not of the correct type.
            NotImplementedError: If `datetime` is specified when cloud rutime is used.
        """
        # pylint: disable=arguments-differ
        if self._configuration.simulator:
            # Simulators do not have backend properties.
            return None
        if not isinstance(refresh, bool):
            raise TypeError(
                "The 'refresh' argument needs to be a boolean. "
                "{} is of type {}".format(refresh, type(refresh))
            )
        if datetime:
            if not isinstance(datetime, python_datetime):
                raise TypeError("'{}' is not of type 'datetime'.")
            if isinstance(self._api_client, RuntimeClient):
                raise NotImplementedError(
                    "'datetime' is not supported by cloud runtime."
                )
            datetime = local_to_utc(datetime)
        if datetime or refresh or self._properties is None:
            api_properties = self._api_client.backend_properties(
                self.name, datetime=datetime
            )
            if not api_properties:
                return None
            backend_properties = properties_from_server_data(api_properties)
            if datetime:  # Don't cache result.
                return backend_properties
            self._properties = backend_properties
        return self._properties

    def status(self) -> BackendStatus:
        """Return the backend status.

        Note:
            If the returned :class:`~qiskit.providers.models.BackendStatus`
            instance has ``operational=True`` but ``status_msg="internal"``,
            then the backend is accepting jobs but not processing them.

        Returns:
            The status of the backend.

        Raises:
            IBMBackendApiProtocolError: If the status for the backend cannot be formatted properly.
        """
        api_status = self._api_client.backend_status(self.name)

        try:
            return BackendStatus.from_dict(api_status)
        except TypeError as ex:
            raise IBMBackendApiProtocolError(
                "Unexpected return value received from the server when "
                "getting backend status: {}".format(str(ex))
            ) from ex

    def defaults(self, refresh: bool = False) -> Optional[PulseDefaults]:
        """Return the pulse defaults for the backend.

        The schema for default pulse configuration can be found in
        `Qiskit/ibm-quantum-schemas
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/default_pulse_configuration_schema.json>`_.

        Args:
            refresh: If ``True``, re-query the server for the backend pulse defaults.
                Otherwise, return a cached version.

        Returns:
            The backend pulse defaults or ``None`` if the backend does not support pulse.
        """
        if refresh or self._defaults is None:
            api_defaults = self._api_client.backend_pulse_defaults(self.name)
            if api_defaults:
                self._defaults = defaults_from_server_data(api_defaults)
            else:
                self._defaults = None

        return self._defaults

    def configuration(
        self,
    ) -> Union[QasmBackendConfiguration, PulseBackendConfiguration]:
        """Return the backend configuration.

        Backend configuration contains fixed information about the backend, such
        as its name, number of qubits, basis gates, coupling map, quantum volume, etc.

        The schema for backend configuration can be found in
        `Qiskit/ibm-quantum-schemas
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/backend_configuration_schema.json>`_.

        Returns:
            The configuration for the backend.
        """
        return self._configuration

    def drive_channel(self, qubit: int) -> DriveChannel:
        """Return the drive channel for the given qubit.

        Returns:
            DriveChannel: The Qubit drive channel
        """
        return self._configuration.drive(qubit=qubit)

    def measure_channel(self, qubit: int) -> MeasureChannel:
        """Return the measure stimulus channel for the given qubit.

        Returns:
            MeasureChannel: The Qubit measurement stimulus line
        """
        return self._configuration.measure(qubit=qubit)

    def acquire_channel(self, qubit: int) -> AcquireChannel:
        """Return the acquisition channel for the given qubit.

        Returns:
            AcquireChannel: The Qubit measurement acquisition line.
        """
        return self._configuration.acquire(qubit=qubit)

    def control_channel(self, qubits: Iterable[int]) -> List[ControlChannel]:
        """Return the secondary drive channel for the given qubit

        This is typically utilized for controlling multiqubit interactions.
        This channel is derived from other channels.

        Args:
            qubits: Tuple or list of qubits of the form
                ``(control_qubit, target_qubit)``.

        Returns:
            List[ControlChannel]: The Qubit measurement acquisition line.
        """
        return self._configuration.control(qubits=qubits)

    def __repr__(self) -> str:
        return "<{}('{}')>".format(self.__class__.__name__, self.name)

    def __call__(self) -> "IBMBackend":
        # For backward compatibility only, can be removed later.
        return self

    def run(self, *args: Any, **kwargs: Any) -> None:
        """Not supported method"""
        # pylint: disable=arguments-differ
        raise RuntimeError(
            "IBMBackend.run() is not supported in the Qiskit Runtime environment."
        )


class IBMRetiredBackend(IBMBackend):
    """Backend class interfacing with an IBM Quantum device no longer available."""

    def __init__(
        self,
        configuration: Union[QasmBackendConfiguration, PulseBackendConfiguration],
        service: "qiskit_runtime_service.QiskitRuntimeService",
        api_client: Optional[AccountClient] = None,
    ) -> None:
        """IBMRetiredBackend constructor.

        Args:
            configuration: Backend configuration.
            service: Instance of QiskitRuntimeService.
            api_client: IBM Quantum client used to communicate with the server.
        """
        super().__init__(configuration, service, api_client)
        self._status = BackendStatus(
            backend_name=self.name,
            backend_version=self.configuration().backend_version,
            operational=False,
            pending_jobs=0,
            status_msg="This backend is no longer available.",
        )

    @classmethod
    def _default_options(cls) -> Options:
        """Default runtime options."""
        return Options(shots=4000)

    def properties(
        self, refresh: bool = False, datetime: Optional[python_datetime] = None
    ) -> None:
        """Return the backend properties."""
        return None

    def defaults(self, refresh: bool = False) -> None:
        """Return the pulse defaults for the backend."""
        return None

    def status(self) -> BackendStatus:
        """Return the backend status."""
        return self._status

    @classmethod
    def from_name(
        cls,
        backend_name: str,
        api: Optional[AccountClient] = None,
    ) -> "IBMRetiredBackend":
        """Return a retired backend from its name."""
        configuration = QasmBackendConfiguration(
            backend_name=backend_name,
            backend_version="0.0.0",
            online_date="2019-10-16T04:00:00Z",
            n_qubits=1,
            basis_gates=[],
            simulator=False,
            local=False,
            conditional=False,
            open_pulse=False,
            memory=False,
            max_shots=1,
            gates=[GateConfig(name="TODO", parameters=[], qasm_def="TODO")],
            coupling_map=[[0, 1]],
            max_experiments=300,
        )
        return cls(configuration, api)
