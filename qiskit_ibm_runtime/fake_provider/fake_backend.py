# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=no-name-in-module
"""
Base class for dummy backends.
"""
import logging
import warnings
import collections
import json
import os
import re

from typing import List, Iterable, Union

from qiskit import circuit, QuantumCircuit

from qiskit.providers import BackendV2, BackendV1
from qiskit import pulse
from qiskit.exceptions import QiskitError
from qiskit.utils import optionals as _optionals
from qiskit.transpiler import Target
from qiskit.providers import Options
from qiskit.providers.fake_provider.utils.json_decoder import (
    decode_backend_configuration,
    decode_backend_properties,
    decode_pulse_defaults,
)

from qiskit.providers.basic_provider import BasicSimulator

from qiskit_ibm_runtime.utils.backend_converter import convert_to_target
from .. import QiskitRuntimeService
from ..utils.backend_encoder import BackendEncoder

from ..models import (
    BackendProperties,
    BackendConfiguration,
    PulseDefaults,
    BackendStatus,
    QasmBackendConfiguration,
    PulseBackendConfiguration,
)
from ..utils.deprecation import issue_deprecation_msg

logger = logging.getLogger(__name__)


class _Credentials:
    def __init__(self, token: str = "123456", url: str = "https://") -> None:
        self.token = token
        self.url = url
        self.hub = "hub"
        self.group = "group"
        self.project = "project"


class FakeBackendV2(BackendV2):
    """A fake backend class for testing and noisy simulation using real backend
    snapshots.

    The class inherits :class:`~qiskit.providers.BackendV2` class. This version
    differs from earlier :class:`~qiskit.providers.fake_provider.FakeBackend` (V1) class in a
    few aspects. Firstly, configuration attribute no longer exsists. Instead,
    attributes exposing equivalent required immutable properties of the backend
    device are added. For example ``fake_backend.configuration().n_qubits`` is
    accessible from ``fake_backend.num_qubits`` now. Secondly, this version
    removes extra abstractions :class:`~qiskit.providers.fake_provider.FakeQasmBackend` and
    :class:`~qiskit.providers.fake_provider.FakePulseBackend` that were present in V1.
    """

    # directory and file names for real backend snapshots.
    dirname = None
    conf_filename = None
    props_filename = None
    defs_filename = None
    backend_name = None

    def __init__(self) -> None:
        """FakeBackendV2 initializer."""
        self._conf_dict = self._get_conf_dict_from_json()
        self._props_dict = None
        self._defs_dict = None
        super().__init__(
            provider=None,
            name=self._conf_dict.get("backend_name"),
            description=self._conf_dict.get("description"),
            online_date=self._conf_dict.get("online_date"),
            backend_version=self._conf_dict.get("backend_version"),
        )
        self._target = None
        self.sim = None

        if "channels" in self._conf_dict:
            self._parse_channels(self._conf_dict["channels"])

    def _parse_channels(self, channels: dict) -> None:
        type_map = {
            "acquire": pulse.AcquireChannel,
            "drive": pulse.DriveChannel,
            "measure": pulse.MeasureChannel,
            "control": pulse.ControlChannel,
        }
        identifier_pattern = re.compile(r"\D+(?P<index>\d+)")

        channels_map = {  # type: ignore
            "acquire": collections.defaultdict(list),
            "drive": collections.defaultdict(list),
            "measure": collections.defaultdict(list),
            "control": collections.defaultdict(list),
        }
        for identifier, spec in channels.items():
            channel_type = spec["type"]
            out = re.match(identifier_pattern, identifier)
            if out is None:
                # Identifier is not a valid channel name format
                continue
            channel_index = int(out.groupdict()["index"])
            qubit_index = tuple(spec["operates"]["qubits"])
            chan_obj = type_map[channel_type](channel_index)
            channels_map[channel_type][qubit_index].append(chan_obj)
        setattr(self, "channels_map", channels_map)

    def _setup_sim(self) -> None:
        if _optionals.HAS_AER:
            from qiskit_aer import AerSimulator  # pylint: disable=import-outside-toplevel

            self.sim = AerSimulator()
            if self.target and self._props_dict:
                noise_model = self._get_noise_model_from_backend_v2()  # type: ignore
                self.sim.set_options(noise_model=noise_model)
                # Update fake backend default too to avoid overwriting
                # it when run() is called
                self.set_options(noise_model=noise_model)

        else:
            self.sim = BasicSimulator()

    def _get_conf_dict_from_json(self) -> dict:
        if not self.conf_filename:
            return None
        conf_dict = self._load_json(self.conf_filename)  # type: ignore
        decode_backend_configuration(conf_dict)
        conf_dict["backend_name"] = self.backend_name
        return conf_dict

    def _set_props_dict_from_json(self) -> None:
        if self.props_filename:
            props_dict = self._load_json(self.props_filename)  # type: ignore
            decode_backend_properties(props_dict)
            self._props_dict = props_dict

    def _set_defs_dict_from_json(self) -> None:
        if self.defs_filename:
            defs_dict = self._load_json(self.defs_filename)  # type: ignore
            decode_pulse_defaults(defs_dict)
            self._defs_dict = defs_dict

    def _supports_dynamic_circuits(self) -> bool:
        supported_features = self._conf_dict.get("supported_features") or []
        return "qasm3" in supported_features

    def _load_json(self, filename: str) -> dict:
        with open(  # pylint: disable=unspecified-encoding
            os.path.join(self.dirname, filename)
        ) as f_json:
            the_json = json.load(f_json)
        return the_json

    def status(self) -> BackendStatus:
        """Return the backend status.

        Returns:
            The status of the backend.

        """

        api_status = {
            "backend_name": self.name,
            "backend_version": "",
            "status_msg": "active",
            "operational": True,
            "pending_jobs": 0,
        }

        return BackendStatus.from_dict(api_status)

    def properties(self, refresh: bool = False) -> BackendProperties:
        """Return the backend properties

        Args:
            refresh: If ``True``, re-retrieve the backend properties
            from the local file.

        Returns:
            The backend properties.
        """
        if refresh or (self._props_dict is None):
            self._set_props_dict_from_json()
        return BackendProperties.from_dict(self._props_dict)

    def defaults(self, refresh: bool = False) -> PulseDefaults:
        """Return the pulse defaults for the backend

        Args:
            refresh: If ``True``, re-retrieve the backend defaults from the
            local file.

        Returns:
            The backend pulse defaults or ``None`` if the backend does not support pulse.
        """
        if refresh or self._defs_dict is None:
            self._set_defs_dict_from_json()
        if self._defs_dict:
            return PulseDefaults.from_dict(self._defs_dict)  # type: ignore[unreachable]
        return None

    def configuration(self) -> Union[QasmBackendConfiguration, PulseBackendConfiguration]:
        """Return the backend configuration."""
        return BackendConfiguration.from_dict(self._conf_dict)

    def check_faulty(self, circuit: QuantumCircuit) -> None:  # pylint: disable=redefined-outer-name
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

    @property
    def target(self) -> Target:
        """A :class:`qiskit.transpiler.Target` object for the backend.

        :rtype: Target
        """
        if self._target is None:
            self._get_conf_dict_from_json()
            if self._props_dict is None:
                self._set_props_dict_from_json()
            if self._defs_dict is None:
                self._set_defs_dict_from_json()
            conf = BackendConfiguration.from_dict(self._conf_dict)
            props = None
            if self._props_dict is not None:
                props = BackendProperties.from_dict(self._props_dict)  # type: ignore
            defaults = None
            if self._defs_dict is not None:
                defaults = PulseDefaults.from_dict(self._defs_dict)  # type: ignore

            self._target = convert_to_target(
                configuration=conf,
                properties=props,
                defaults=defaults,
                # Fake backends use the simulator backend.
                # This doesn't have the exclusive constraint.
                include_control_flow=True,
                include_fractional_gates=True,
            )

        return self._target

    @property
    def max_circuits(self) -> None:
        return None

    @classmethod
    def _default_options(cls) -> Options:
        """Return the default options

        This method will return a :class:`qiskit.providers.Options`
        subclass object that will be used for the default options. These
        should be the default parameters to use for the options of the
        backend.

        Returns:
            qiskit.providers.Options: A options object with
                default values set
        """
        if _optionals.HAS_AER:
            from qiskit_aer import AerSimulator  # pylint: disable=import-outside-toplevel

            return AerSimulator._default_options()
        else:
            return BasicSimulator._default_options()

    @property
    def dtm(self) -> float:
        """Return the system time resolution of output signals

        Returns:
            The output signal timestep in seconds.
        """
        dtm = self._conf_dict.get("dtm")
        if dtm is not None:
            # converting `dtm` in nanoseconds in configuration file to seconds
            return dtm * 1e-9
        else:
            return None

    @property
    def meas_map(self) -> List[List[int]]:
        """Return the grouping of measurements which are multiplexed
        This is required to be implemented if the backend supports Pulse
        scheduling.

        Returns:
            The grouping of measurements which are multiplexed
        """
        return self._conf_dict.get("meas_map")

    def drive_channel(self, qubit: int):  # type: ignore
        """Return the drive channel for the given qubit.

        This is required to be implemented if the backend supports Pulse
        scheduling.

        Returns:
            DriveChannel: The Qubit drive channel
        """
        drive_channels_map = getattr(self, "channels_map", {}).get("drive", {})
        qubits = (qubit,)
        if qubits in drive_channels_map:
            return drive_channels_map[qubits][0]
        return None

    def measure_channel(self, qubit: int):  # type: ignore
        """Return the measure stimulus channel for the given qubit.

        This is required to be implemented if the backend supports Pulse
        scheduling.

        Returns:
            MeasureChannel: The Qubit measurement stimulus line
        """
        measure_channels_map = getattr(self, "channels_map", {}).get("measure", {})
        qubits = (qubit,)
        if qubits in measure_channels_map:
            return measure_channels_map[qubits][0]
        return None

    def acquire_channel(self, qubit: int):  # type: ignore
        """Return the acquisition channel for the given qubit.

        This is required to be implemented if the backend supports Pulse
        scheduling.

        Returns:
            AcquireChannel: The Qubit measurement acquisition line.
        """
        acquire_channels_map = getattr(self, "channels_map", {}).get("acquire", {})
        qubits = (qubit,)
        if qubits in acquire_channels_map:
            return acquire_channels_map[qubits][0]
        return None

    def control_channel(self, qubits: Iterable[int]):  # type: ignore
        """Return the secondary drive channel for the given qubit

        This is typically utilized for controlling multiqubit interactions.
        This channel is derived from other channels.

        This is required to be implemented if the backend supports Pulse
        scheduling.

        Args:
            qubits: Tuple or list of qubits of the form
                ``(control_qubit, target_qubit)``.

        Returns:
            List[ControlChannel]: The multi qubit control line.
        """
        control_channels_map = getattr(self, "channels_map", {}).get("control", {})
        qubits = tuple(qubits)
        if qubits in control_channels_map:
            return control_channels_map[qubits]
        return []

    def run(self, run_input, **options):  # type: ignore
        """Run on the fake backend using a simulator.

        This method runs circuit jobs (an individual or a list of QuantumCircuit
        ) and pulse jobs (an individual or a list of Schedule or ScheduleBlock)
        using BasicSimulator or Aer simulator and returns a
        :class:`~qiskit.providers.Job` object.

        If qiskit-aer is installed, jobs will be run using AerSimulator with
        noise model of the fake backend. Otherwise, jobs will be run using
        BasicSimulator without noise.

        Currently noisy simulation of a pulse job is not supported yet in
        FakeBackendV2.

        Args:
            run_input (QuantumCircuit or Schedule or ScheduleBlock or list): An
                individual or a list of
                :class:`~qiskit.circuit.QuantumCircuit`,
                :class:`~qiskit.pulse.ScheduleBlock`, or
                :class:`~qiskit.pulse.Schedule` objects to run on the backend.
            options: Any kwarg options to pass to the backend for running the
                config. If a key is also present in the options
                attribute/object then the expectation is that the value
                specified will be used instead of what's set in the options
                object.

        Returns:
            Job: The job object for the run

        Raises:
            QiskitError: If a pulse job is supplied and qiskit-aer is not installed.
        """
        circuits = run_input
        pulse_job = None
        if isinstance(circuits, (pulse.Schedule, pulse.ScheduleBlock)):
            pulse_job = True
        elif isinstance(circuits, circuit.QuantumCircuit):
            pulse_job = False
        elif isinstance(circuits, list):
            if circuits:
                if all(isinstance(x, (pulse.Schedule, pulse.ScheduleBlock)) for x in circuits):
                    pulse_job = True
                elif all(isinstance(x, circuit.QuantumCircuit) for x in circuits):
                    pulse_job = False
        if pulse_job is None:  # submitted job is invalid
            raise QiskitError(
                "Invalid input object %s, must be either a "
                "QuantumCircuit, Schedule, or a list of either" % circuits
            )
        if pulse_job:  # pulse job
            raise QiskitError("Pulse simulation is currently not supported for V2 fake backends.")
        # circuit job
        if not _optionals.HAS_AER:
            warnings.warn(
                "Aer not found, using qiskit.BasicSimulator and no noise.", RuntimeWarning
            )
        if self.sim is None:
            self._setup_sim()
        self.sim._options = self._options
        job = self.sim.run(circuits, **options)
        return job

    def _get_noise_model_from_backend_v2(  # type: ignore
        self,
        gate_error=True,
        readout_error=True,
        thermal_relaxation=True,
        temperature=0,
        gate_lengths=None,
        gate_length_units="ns",
    ):
        """Build noise model from BackendV2.

        This is a temporary fix until qiskit-aer supports building noise model
        from a BackendV2 object.
        """

        from qiskit.circuit import Delay  # pylint: disable=import-outside-toplevel
        from qiskit.providers.exceptions import (  # pylint: disable=import-outside-toplevel
            BackendPropertyError,
        )
        from qiskit_aer.noise import NoiseModel  # pylint: disable=import-outside-toplevel
        from qiskit_aer.noise.device.models import (  # pylint: disable=import-outside-toplevel
            _excited_population,
            basic_device_gate_errors,
            basic_device_readout_errors,
        )
        from qiskit_aer.noise.passes import (  # pylint: disable=import-outside-toplevel
            RelaxationNoisePass,
        )

        if self._props_dict is None:
            self._set_props_dict_from_json()

        properties = BackendProperties.from_dict(self._props_dict)
        basis_gates = self.operation_names
        num_qubits = self.num_qubits
        dt = self.dt  # pylint: disable=invalid-name

        noise_model = NoiseModel(basis_gates=basis_gates)

        # Add single-qubit readout errors
        if readout_error:
            for qubits, error in basic_device_readout_errors(properties):
                noise_model.add_readout_error(error, qubits)

        # Add gate errors
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                module="qiskit_aer.noise.device.models",
            )
            gate_errors = basic_device_gate_errors(
                properties,
                gate_error=gate_error,
                thermal_relaxation=thermal_relaxation,
                gate_lengths=gate_lengths,
                gate_length_units=gate_length_units,
                temperature=temperature,
            )
        for name, qubits, error in gate_errors:
            noise_model.add_quantum_error(error, name, qubits)

        if thermal_relaxation:
            # Add delay errors via RelaxationNiose pass
            try:
                excited_state_populations = [
                    _excited_population(freq=properties.frequency(q), temperature=temperature)
                    for q in range(num_qubits)
                ]
            except BackendPropertyError:
                excited_state_populations = None
            try:
                delay_pass = RelaxationNoisePass(
                    t1s=[properties.t1(q) for q in range(num_qubits)],
                    t2s=[properties.t2(q) for q in range(num_qubits)],
                    dt=dt,
                    op_types=Delay,
                    excited_state_populations=excited_state_populations,
                )
                noise_model._custom_noise_passes.append(delay_pass)
            except BackendPropertyError:
                # Device does not have the required T1 or T2 information
                # in its properties
                pass

        return noise_model

    def refresh(self, service: QiskitRuntimeService) -> None:
        """Update the data files from its real counterpart

        This method pulls the latest backend data files from their real counterpart and
        overwrites the corresponding files in the local installation:
        *  ../fake_provider/backends/{backend_name}/conf_{backend_name}.json
        *  ../fake_provider/backends/{backend_name}/defs_{backend_name}.json
        *  ../fake_provider/backends/{backend_name}/props_{backend_name}.json

        The new data files will persist through sessions so the files will stay updated unless they
         are manually reverted locally or when qiskit-ibm-runtime is upgraded/reinstalled.

        Args:
            service: A :class:`QiskitRuntimeService` instance

        Raises:
            ValueError: if the provided service is a non-QiskitRuntimeService instance.
            Exception: If the real target doesn't exist or can't be accessed
        """
        if not isinstance(service, QiskitRuntimeService):
            raise ValueError(
                "The provided service to update the fake backend is invalid. A QiskitRuntimeService is"
                " required to retrieve the real backend's current properties and settings."
            )

        version = self.backend_version
        prod_name = self.backend_name.replace("fake", "ibm")
        try:
            backends = service.backends(prod_name)
            real_backend = backends[0]

            real_props = real_backend.properties()
            real_config = real_backend.configuration()
            real_defs = real_backend.defaults()

            updated_config = real_config.to_dict()
            updated_config["backend_name"] = self.backend_name

            if updated_config != self._conf_dict:

                if real_config:
                    config_path = os.path.join(self.dirname, self.conf_filename)
                    with open(config_path, "w", encoding="utf-8") as fd:
                        fd.write(json.dumps(real_config.to_dict(), cls=BackendEncoder))

                if real_props:
                    props_path = os.path.join(self.dirname, self.props_filename)
                    with open(props_path, "w", encoding="utf-8") as fd:
                        fd.write(json.dumps(real_props.to_dict(), cls=BackendEncoder))

                if real_defs:
                    defs_path = os.path.join(self.dirname, self.defs_filename)
                    with open(defs_path, "w", encoding="utf-8") as fd:
                        fd.write(json.dumps(real_defs.to_dict(), cls=BackendEncoder))

                if self._target is not None:
                    self._conf_dict = self._get_conf_dict_from_json()  # type: ignore[unreachable]
                    self._set_props_dict_from_json()
                    self._set_defs_dict_from_json()

                    updated_configuration = BackendConfiguration.from_dict(self._conf_dict)
                    updated_properties = BackendProperties.from_dict(self._props_dict)
                    updated_defaults = PulseDefaults.from_dict(self._defs_dict)

                    self._target = convert_to_target(
                        configuration=updated_configuration,
                        properties=updated_properties,
                        defaults=updated_defaults,
                        include_control_flow=True,
                        include_fractional_gates=True,
                    )

                logger.info(
                    "The backend %s has been updated from version %s to %s version.",
                    self.backend_name,
                    version,
                    real_props.backend_version,
                )
            else:
                logger.info("There are no available new updates for %s.", self.backend_name)
        except Exception as ex:  # pylint: disable=broad-except
            logger.warning("The refreshing of %s has failed: %s", self.backend_name, str(ex))


class FakeBackend(BackendV1):
    """This is a dummy backend just for testing purposes."""

    def __init__(self, configuration, time_alive=10):  # type: ignore
        """FakeBackend initializer.

        Args:
            configuration (BackendConfiguration): backend configuration
            time_alive (int): time to wait before returning result
        """
        issue_deprecation_msg(
            "V1 fake backends are deprecated",
            "0.24",
            "Please use V2 fake backends instead.",
            stacklevel=3,
        )
        super().__init__(configuration)
        self.time_alive = time_alive
        self._credentials = _Credentials()
        self.sim = None

    def _setup_sim(self) -> None:
        if _optionals.HAS_AER:
            from qiskit_aer import AerSimulator  # pylint: disable=import-outside-toplevel
            from qiskit_aer.noise import NoiseModel  # pylint: disable=import-outside-toplevel

            self.sim = AerSimulator()
            if self.properties():
                noise_model = NoiseModel.from_backend(self)
                self.sim.set_options(noise_model=noise_model)
                # Update fake backend default options too to avoid overwriting
                # it when run() is called
                self.set_options(noise_model=noise_model)
        else:
            self.sim = BasicSimulator()

    def properties(self) -> BackendProperties:
        """Return backend properties"""
        coupling_map = self.configuration().coupling_map
        if coupling_map is None:
            return None
        unique_qubits = list(set().union(*coupling_map))

        properties = {
            "backend_name": self.name(),
            "backend_version": self.configuration().backend_version,
            "last_update_date": "2000-01-01 00:00:00Z",
            "qubits": [
                [
                    {"date": "2000-01-01 00:00:00Z", "name": "T1", "unit": "\u00b5s", "value": 0.0},
                    {"date": "2000-01-01 00:00:00Z", "name": "T2", "unit": "\u00b5s", "value": 0.0},
                    {
                        "date": "2000-01-01 00:00:00Z",
                        "name": "frequency",
                        "unit": "GHz",
                        "value": 0.0,
                    },
                    {
                        "date": "2000-01-01 00:00:00Z",
                        "name": "readout_error",
                        "unit": "",
                        "value": 0.0,
                    },
                    {"date": "2000-01-01 00:00:00Z", "name": "operational", "unit": "", "value": 1},
                ]
                for _ in range(len(unique_qubits))
            ],
            "gates": [
                {
                    "gate": "cx",
                    "name": "CX" + str(pair[0]) + "_" + str(pair[1]),
                    "parameters": [
                        {
                            "date": "2000-01-01 00:00:00Z",
                            "name": "gate_error",
                            "unit": "",
                            "value": 0.0,
                        }
                    ],
                    "qubits": [pair[0], pair[1]],
                }
                for pair in coupling_map
            ],
            "general": [],
        }

        return BackendProperties.from_dict(properties)

    @classmethod
    def _default_options(cls) -> Options:
        if _optionals.HAS_AER:
            from qiskit_aer import QasmSimulator  # pylint: disable=import-outside-toplevel

            return QasmSimulator._default_options()
        else:
            return BasicSimulator._default_options()

    def run(self, run_input, **kwargs):  # type: ignore
        """Main job in simulator"""
        circuits = run_input
        pulse_job = None
        if isinstance(circuits, (pulse.Schedule, pulse.ScheduleBlock)):
            pulse_job = True
        elif isinstance(circuits, circuit.QuantumCircuit):
            pulse_job = False
        elif isinstance(circuits, list):
            if circuits:
                if all(isinstance(x, (pulse.Schedule, pulse.ScheduleBlock)) for x in circuits):
                    pulse_job = True
                elif all(isinstance(x, circuit.QuantumCircuit) for x in circuits):
                    pulse_job = False
        if pulse_job is None:
            raise QiskitError(
                "Invalid input object %s, must be either a "
                "QuantumCircuit, Schedule, or a list of either" % circuits
            )
        if pulse_job:  # pulse job
            raise QiskitError("Pulse simulation is currently not supported for V1 fake backends.")

        if self.sim is None:
            self._setup_sim()
        if not _optionals.HAS_AER:
            warnings.warn(
                "Aer not found, using qiskit.BasicSimulator and no noise.", RuntimeWarning
            )
        self.sim._options = self._options
        job = self.sim.run(circuits, **kwargs)

        return job
