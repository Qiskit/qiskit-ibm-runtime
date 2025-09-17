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
from typing import Any
import logging
import warnings
import json
import os

from qiskit import QuantumCircuit

from qiskit.providers import BackendV2
from qiskit.utils import optionals as _optionals
from qiskit.transpiler import Target
from qiskit.providers import Options

from qiskit.providers.basic_provider import BasicSimulator

from qiskit_ibm_runtime.utils.backend_converter import convert_to_target
from qiskit_ibm_runtime.utils.backend_decoder import (
    decode_backend_configuration,
    properties_from_server_data,
)

from .. import QiskitRuntimeService
from ..utils.backend_encoder import BackendEncoder
from ..utils.backend_decoder import configuration_from_server_data

from ..models import (
    BackendProperties,
    BackendConfiguration,
    BackendStatus,
    QasmBackendConfiguration,
)
from ..models.exceptions import (
    BackendPropertyError,
)

logger = logging.getLogger(__name__)


class FakeBackendV2(BackendV2):
    """A fake backend class for testing and noisy simulation using real backend
    snapshots.
    """

    # directory and file names for real backend snapshots.
    dirname = None
    conf_filename = None
    props_filename = None
    backend_name = None

    def __init__(self) -> None:
        """FakeBackendV2 initializer."""
        self._conf_dict = self._get_conf_dict_from_json()
        self._props_dict = None
        super().__init__(
            provider=None,
            name=self._conf_dict.get("backend_name"),
            description=self._conf_dict.get("description"),
            online_date=self._conf_dict.get("online_date"),
            backend_version=self._conf_dict.get("backend_version"),
        )
        self._target = None
        self.sim = None

    def __getattr__(self, name: str) -> Any:
        """Gets attribute from self or configuration

        This magic method executes when user accesses an attribute that
        does not yet exist on the class.
        """
        # Prevent recursion since these properties are accessed within __getattr__
        if name in ["_target", "_conf_dict", "_props_dict"]:
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(self.__class__.__name__, name)
            )

        # Check if the attribute now is available in backend configuration
        try:
            return self.configuration().__getattribute__(name)
        except AttributeError:
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(self.__class__.__name__, name)
            )

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
            properties_from_server_data(props_dict)
            self._props_dict = props_dict

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
            refresh: If ``True``, re-retrieve the backend properties from the local file.

        Returns:
            The backend properties.
        """
        if refresh or (self._props_dict is None):
            self._set_props_dict_from_json()
        return BackendProperties.from_dict(self._props_dict)

    def configuration(self) -> QasmBackendConfiguration:
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
            conf = BackendConfiguration.from_dict(self._conf_dict)
            props = None
            if self._props_dict is not None:
                props = BackendProperties.from_dict(self._props_dict)  # type: ignore

            self._target = convert_to_target(
                configuration=conf,
                properties=props,
                # Fake backends use the simulator backend.
                # This doesn't have the exclusive constraint.
                include_control_flow=True,
                include_fractional_gates=True,
            )

        return self._target

    @property
    def max_circuits(self) -> None:
        """This property used to return the `max_experiments` value from the
        backend configuration but this value is no longer an accurate representation
        of backend circuit limits. New fields will be added to indicate new limits.
        """

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

    def run(self, run_input, **options):  # type: ignore
        """Run on the fake backend using a simulator.

        This method runs circuit jobs (an individual or a list of QuantumCircuit)
        using BasicSimulator or Aer simulator and returns a
        :class:`~qiskit.providers.Job` object.

        If qiskit-aer is installed, jobs will be run using AerSimulator with
        noise model of the fake backend. Otherwise, jobs will be run using
        BasicSimulator without noise.

        Currently noisy simulation of a pulse job is not supported yet in
        FakeBackendV2.

        Args:
            run_input (QuantumCircuit or list): An
                individual or a list of
                :class:`~qiskit.circuit.QuantumCircuit`
            options: Any kwarg options to pass to the backend for running the
                config. If a key is also present in the options
                attribute/object then the expectation is that the value
                specified will be used instead of what's set in the options
                object.

        Returns:
            Job: The job object for the run
        """
        if self.sim is None:
            self._setup_sim()
        self.sim._options = self._options
        job = self.sim.run(run_input, **options)
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
        basis_gates = self.configuration().basis_gates
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

    def refresh(self, service: QiskitRuntimeService, use_fractional_gates: bool = False) -> None:
        """Update the data files from its real counterpart

        This method pulls the latest backend data files from their real counterpart and
        overwrites the corresponding files in the local installation:

        *  ``../fake_provider/backends/{backend_name}/conf_{backend_name}.json``
        *  ``../fake_provider/backends/{backend_name}/defs_{backend_name}.json``
        *  ``../fake_provider/backends/{backend_name}/props_{backend_name}.json``

        The new data files will persist through sessions so the files will stay updated unless they
        are manually reverted locally or when ``qiskit-ibm-runtime`` is upgraded or reinstalled.

        Args:
            service: A :class:`QiskitRuntimeService` instance
            use_fractional_gates: Set True to allow for the backends to include
                fractional gates.

        Raises:
            ValueError: if the provided service is a non-QiskitRuntimeService instance.
            Exception: If the real target doesn't exist or can't be accessed
        """
        if not isinstance(service, QiskitRuntimeService):
            raise ValueError(
                "The provided service to update the fake backend is invalid. A QiskitRuntimeService is"
                " required to retrieve the real backend's current properties and settings."
            )

        prod_name = self.backend_name.replace("fake", "ibm")
        try:
            backends = service.backends(prod_name, use_fractional_gates=use_fractional_gates)
            real_backend = backends[0]

            real_props = real_backend.properties(refresh=True)
            real_config = configuration_from_server_data(
                raw_config=service._get_api_client().backend_configuration(prod_name, refresh=True),
                use_fractional_gates=use_fractional_gates,
            )

            updated_config = real_config.to_dict()
            updated_config["backend_name"] = self.backend_name

            if real_config:
                config_path = os.path.join(self.dirname, self.conf_filename)
                with open(config_path, "w", encoding="utf-8") as fd:
                    fd.write(json.dumps(real_config.to_dict(), cls=BackendEncoder))

            if real_props:
                props_path = os.path.join(self.dirname, self.props_filename)
                with open(props_path, "w", encoding="utf-8") as fd:
                    fd.write(json.dumps(real_props.to_dict(), cls=BackendEncoder))

            self._conf_dict = self._get_conf_dict_from_json()  # type: ignore[unreachable]
            self._set_props_dict_from_json()

            updated_configuration = BackendConfiguration.from_dict(self._conf_dict)
            updated_properties = BackendProperties.from_dict(self._props_dict)

            self._target = convert_to_target(
                configuration=updated_configuration,
                properties=updated_properties,
                include_control_flow=True,
                include_fractional_gates=True,
            )

            logger.info(
                "The backend %s has been updated with the latest data from the server.",
                self.backend_name,
            )

        except Exception as ex:  # pylint: disable=broad-except
            logger.warning("The refreshing of %s has failed: %s", self.backend_name, str(ex))
