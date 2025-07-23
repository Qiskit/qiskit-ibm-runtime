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
from typing import Optional, Any, List
from datetime import datetime as python_datetime
from copy import deepcopy
from packaging.version import Version

from qiskit import QuantumCircuit, __version__ as qiskit_version
from qiskit.providers.backend import BackendV2 as Backend
from qiskit.providers.options import Options
from qiskit.transpiler.target import Target

from .models import (
    BackendStatus,
    BackendProperties,
    GateConfig,
    QasmBackendConfiguration,
)

from . import qiskit_runtime_service  # pylint: disable=unused-import,cyclic-import

from .api.clients import RuntimeClient
from .exceptions import (
    IBMBackendApiProtocolError,
    IBMBackendError,
)
from .utils.backend_converter import convert_to_target

from .utils.backend_decoder import (
    properties_from_server_data,
    configuration_from_server_data,
)
from .utils import local_to_utc

if Version(qiskit_version).major >= 2:
    from qiskit.result import MeasLevel, MeasReturnType
else:
    from qiskit.qobj.utils import MeasLevel, MeasReturnType  # pylint: disable=import-error


logger = logging.getLogger(__name__)

QOBJRUNNERPROGRAMID = "circuit-runner"
QASM3RUNNERPROGRAMID = "qasm3-runner"


class IBMBackend(Backend):
    """Backend class interfacing with an IBM Quantum backend.

    Note:

        * You should not instantiate the ``IBMBackend`` class directly. Instead, use
          the methods provided by an :class:`QiskitRuntimeService` instance to retrieve and handle
          backends.

    This class represents an IBM Quantum backend. Its attributes and methods provide
    information about the backend. For example, the :meth:`status()` method
    returns a :class:`BackendStatus<~.providers.models.BackendStatus>` instance.
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
        * coupling_map (list): The coupling map for the device
        * supported_instructions (List[str]): Instructions supported by the backend.
        * dynamic_reprate_enabled (bool): whether delay between primitives can be set dynamically
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
        configuration: QasmBackendConfiguration,
        service: "qiskit_runtime_service.QiskitRuntimeService",
        api_client: RuntimeClient,
        instance: Optional[str] = None,
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
        self._instance = instance
        self._service = service
        self._api_client = api_client
        self._configuration = deepcopy(configuration)
        self._properties: Any = None
        self._target: Any = None
        if (
            not self._configuration.simulator
            and hasattr(self.options, "noise_model")
            and hasattr(self.options, "seed_simulator")
        ):
            self.options.set_validator("noise_model", type(None))
            self.options.set_validator("seed_simulator", type(None))
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
        # Prevent recursion since these properties are accessed within __getattr__
        if name in ["_properties", "_target", "_configuration"]:
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(self.__class__.__name__, name)
            )

        # Lazy load properties and pulse defaults and construct the target object.
        self.properties()
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
                "'{}' object has no attribute '{}'".format(self.__class__.__name__, name)
            )

    def _convert_to_target(self, refresh: bool = False) -> None:
        """Converts backend configuration and properties to Target object"""
        if refresh or not self._target:
            self._target = convert_to_target(
                configuration=self._configuration,  # type: ignore[arg-type]
                properties=self._properties,
            )

    @classmethod
    def _default_options(cls) -> Options:
        """Default runtime options."""
        return Options(
            shots=4000,
            memory=False,
            meas_level=MeasLevel.CLASSIFIED,
            meas_return=MeasReturnType.AVERAGE,
            memory_slots=None,
            memory_slot_size=100,
            rep_time=None,
            rep_delay=None,
            init_qubits=True,
            use_measure_esp=None,
            use_fractional_gates=False,
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
    def max_circuits(self) -> None:
        """This property used to return the `max_experiments` value from the
        backend configuration but this value is no longer an accurate representation
        of backend circuit limits. New fields will be added to indicate new limits.
        """

        return None

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
        self.properties()
        self._convert_to_target()
        return self._target

    def target_history(self, datetime: Optional[python_datetime] = None) -> Target:
        """A :class:`qiskit.transpiler.Target` object for the backend.

        Returns:
            Target with properties found on `datetime`
        """

        return convert_to_target(
            configuration=self._configuration,  # type: ignore[arg-type]
            properties=self.properties(datetime=datetime),  # pylint: disable=unexpected-keyword-arg
        )

    def refresh(self) -> None:
        """Retrieve the newest backend configuration and refresh the current backend target."""
        if config := configuration_from_server_data(
            raw_config=self._service._get_api_client(self._instance).backend_configuration(
                self.name, refresh=True
            ),
            instance=self._instance,
            use_fractional_gates=self.options.use_fractional_gates,
        ):
            self._configuration = config
        self.properties(refresh=True)  # pylint: disable=unexpected-keyword-arg
        self._convert_to_target(refresh=True)

    def properties(
        self, refresh: bool = False, datetime: Optional[python_datetime] = None
    ) -> Optional[BackendProperties]:
        """Return the backend properties, subject to optional filtering.

        This data describes qubits properties (such as T1 and T2),
        gates properties (such as gate length and error), and other general
        properties of the backend.

        The schema for backend properties can be found in
        `Qiskit/ibm-quantum-schemas/backend_properties
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/backend_properties_schema.json>`_.

        Args:
            refresh: If ``True``, re-query the server for the backend properties.
                Otherwise, return a cached version.
            datetime: By specifying `datetime`, this function returns an instance
                of the :class:`BackendProperties<~.providers.models.BackendProperties>`
                whose timestamp is closest to, but older than, the specified `datetime`.

        Returns:
            The backend properties or ``None`` if the backend properties are not
            currently available.

        Raises:
            TypeError: If an input argument is not of the correct type.
            NotImplementedError: If `datetime` is specified when cloud runtime is used.
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
            datetime = local_to_utc(datetime)
        if datetime or refresh or self._properties is None:
            api_properties = self._api_client.backend_properties(self.name, datetime=datetime)
            if not api_properties:
                return None
            backend_properties = properties_from_server_data(
                api_properties,
                use_fractional_gates=self.options.use_fractional_gates,
            )
            if datetime:  # Don't cache result.
                return backend_properties
            self._properties = backend_properties
        return self._properties

    def status(self) -> BackendStatus:
        """Return the backend status.

        Note:
            If the returned :class:`~.providers.models.BackendStatus`
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

    def configuration(
        self,
    ) -> QasmBackendConfiguration:
        """Return the backend configuration.

        Backend configuration contains fixed information about the backend, such
        as its name, number of qubits, basis gates, coupling map, quantum volume, etc.

        The schema for backend configuration can be found in
        `Qiskit/ibm-quantum-schemas/backend_configuration
        <https://github.com/Qiskit/ibm-quantum-schemas/blob/main/schemas/backend_configuration_schema.json>`_.

        More details about backend configuration properties can be found here `QasmBackendConfiguration
        <https://quantum.cloud.ibm.com/docs/api/qiskit/1.4/qiskit.providers.models.QasmBackendConfiguration>`_.

        IBM backends may also include the following properties:
            * ``supported_features``: a list of strings of supported features like "qasm3" for dynamic
                circuits support.
            * ``parallel_compilation``: a boolean of whether or not the backend can process multiple
                jobs at once. Parts of the classical computation will be parallelized.

        Returns:
            The configuration for the backend.
        """
        return self._configuration

    def __repr__(self) -> str:
        return "<{}('{}')>".format(self.__class__.__name__, self.name)

    def __call__(self) -> "IBMBackend":
        # For backward compatibility only, can be removed later.
        return self

    def check_faulty(self, circuit: QuantumCircuit) -> None:
        """Check if the input circuit uses faulty qubits or edges.

        Args:
            circuit: Circuit to check.

        Raises:
            ValueError: If an instruction operating on a faulty qubit or edge is found.
        """
        if not self.properties():
            return

        faulty_qubits = self.properties().faulty_qubits()
        faulty_gates = self.properties().faulty_gates()
        faulty_edges = [tuple(gate.qubits) for gate in faulty_gates if len(gate.qubits) > 1]

        for instr in circuit.data:
            if instr.operation.name == "barrier":
                continue
            qubit_indices = tuple(circuit.find_bit(x).index for x in instr.qubits)

            for circ_qubit in qubit_indices:
                if circ_qubit in faulty_qubits:
                    raise ValueError(
                        f"Circuit {circuit.name} contains instruction "
                        f"{instr} operating on a faulty qubit {circ_qubit}."
                    )

            if len(qubit_indices) == 2 and qubit_indices in faulty_edges:
                raise ValueError(
                    f"Circuit {circuit.name} contains instruction "
                    f"{instr} operating on a faulty edge {qubit_indices}"
                )

    def __deepcopy__(self, _memo: dict = None) -> "IBMBackend":
        cpy = IBMBackend(
            configuration=deepcopy(self.configuration()),
            service=self._service,
            api_client=deepcopy(self._api_client),
            instance=self._instance,
        )
        cpy.name = self.name
        cpy.description = self.description
        cpy.online_date = self.online_date
        cpy.backend_version = self.backend_version
        cpy._coupling_map = self._coupling_map
        cpy._target = deepcopy(self._target, _memo)
        cpy._options = deepcopy(self._options, _memo)
        return cpy

    def run(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """
        Raises:
            IBMBackendError: The run() method is no longer supported.

        """
        raise IBMBackendError(
            "Support for backend.run() has been removed. Please see our migration guide "
            "https://quantum.cloud.ibm.com/docs/migration-guides/qiskit-runtime for instructions "
            "on how to migrate to the primitives interface."
        )

    def get_translation_stage_plugin(self) -> str:
        """Return the default translation stage plugin name for IBM backends."""
        if not self.options.use_fractional_gates:
            return "ibm_dynamic_circuits"
        return "ibm_fractional"


class IBMRetiredBackend(IBMBackend):
    """Backend class interfacing with an IBM Quantum device no longer available."""

    def __init__(
        self,
        configuration: QasmBackendConfiguration,
        service: "qiskit_runtime_service.QiskitRuntimeService",
        api_client: Optional[RuntimeClient] = None,
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

    def properties(self, refresh: bool = False, datetime: Optional[python_datetime] = None) -> None:
        """Return the backend properties."""
        return None

    def status(self) -> BackendStatus:
        """Return the backend status."""
        return self._status

    @classmethod
    def from_name(
        cls,
        backend_name: str,
        api: Optional[RuntimeClient] = None,
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
            gates=[GateConfig(name="TODO", parameters=[], qasm_def="TODO")],
            coupling_map=[[0, 1]],
        )
        return cls(configuration, api)
