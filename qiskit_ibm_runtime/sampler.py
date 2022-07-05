# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Sampler primitive."""

from typing import Dict, Iterable, Optional, Sequence, Any, Union

from qiskit.circuit import QuantumCircuit, Parameter

# TODO import BaseSampler and SamplerResult from terra once released
from .qiskit.primitives import BaseSampler, SamplerResult
from .exceptions import IBMInputValueError
from .ibm_backend import IBMBackend
from .qiskit_runtime_service import QiskitRuntimeService
from .runtime_session import RuntimeSession
from .utils.converters import hms_to_seconds


class Sampler(BaseSampler):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    Qiskit Runtime Sampler primitive service calculates probabilities or quasi-probabilities
    of bitstrings from quantum circuits.

    Sampler can be initialized with following parameters.

    * circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
        a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

    * parameters: a list of parameters of the quantum circuits.
        (:class:`~qiskit.circuit.parametertable.ParameterView` or
        a list of :class:`~qiskit.circuit.Parameter`) specifying the order
        in which parameter values will be bound.

    * skip_transpilation: Transpilation is skipped if set to True.
        False by default.

    * service: Optional instance of :class:`qiskit_ibm_runtime.QiskitRuntimeService` class,
        defaults to `QiskitRuntimeService()` which tries to initialize your default saved account.

    * options: Runtime options dictionary that control the execution environment.

        * backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
            string name of backend, if not specified a backend will be selected
            automatically (IBM Cloud only).
        * image: the runtime image used to execute the program, specified in
            the form of ``image_name:tag``. Not all accounts are
            authorized to select a different image.
        * log_level: logging level to set in the execution environment. The valid
            log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
            The default level is ``WARNING``.

    The returned instance can be called repeatedly with the following parameters to
    calculate probabilities or quasi-probabilities.

    * circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
        a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or a list of
        circuit indices.

    * parameter_values: An optional list of concrete parameters to be bound.

    * circuit_indices: (DEPRECATED) A list of circuit indices.

    All the above lists should be of the same length.

    Example::

        from qiskit import QuantumCircuit
        from qiskit.circuit.library import RealAmplitudes

        from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

        service = QiskitRuntimeService(channel="ibm_cloud")
        options = { "backend": "ibmq_qasm_simulator" }

        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()

        # executes a Bell circuit
        with Sampler(circuits=[bell], service=service, options=options) as sampler:
            # pass circuits as indices
            result = sampler(circuits=[0], parameter_values=[[]])
            print(result)

        # executes three Bell circuits
        with Sampler(circuits=[bell]*3, service=service, options=options) as sampler:
            # alternatively you can also pass circuits as objects
            result = sampler(circuits=[bell]*3, parameter_values=[[]]*3)
            print(result)

        # parameterized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with Sampler(circuits=[pqc, pqc2], service=service, options=options) as sampler:
            result = sampler(circuits=[0, 0, 1], parameter_values=[theta1, theta2, theta3])
            print(result)
    """

    def __init__(
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        service: Optional[QiskitRuntimeService] = None,
        options: Optional[Dict] = None,
        skip_transpilation: Optional[bool] = False,
        transpilation_settings: Optional[Dict] = None,
        resilience_settings: Optional[Dict] = None,
        max_time: Optional[Union[int, str]] = None,
    ):
        """Initializes the Sampler primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            parameters: A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`)

            service: Optional instance of :class:`qiskit_ibm_runtime.QiskitRuntimeService` class,
                defaults to `QiskitRuntimeService()` which tries to initialize your default
                saved account.

            options: Runtime options dictionary that control the execution environment.

                * backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                    string name of backend, if not specified a backend will be selected
                    automatically (IBM Cloud only).
                * image: the runtime image used to execute the program, specified in
                    the form of ``image_name:tag``. Not all accounts are
                    authorized to select a different image.
                * log_level: logging level to set in the execution environment. The valid
                    log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
                    The default level is ``WARNING``.

            skip_transpilation: Transpilation is skipped if set to True. False by default.

            transpilation_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Qiskit transpiler settings. The transpilation process converts
                operations in the circuit to those supported by the backend, swaps qubits with the
                circuit to overcome limited qubit connectivity and some optimizations to reduce the
                circuit's gate count where it can.

                * skip_transpilation: Transpilation is skipped if set to True.
                    False by default.

                * optimization_settings:

                    * level: How much optimization to perform on the circuits.
                        Higher levels generate more optimized circuits,
                        at the expense of longer transpilation times.
                        * 0: no optimization
                        * 1: light optimization
                        * 2: heavy optimization
                        * 3: even heavier optimization
                        If ``None``, level 3 will be chosen as default.

            resilience_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Using these settings allows you to build resilient algorithms by
                leveraging the state of the art error suppression, mitigation and correction techniques.

                * level: How much resilience to build against errors.
                    Higher levels generate more accurate results,
                    at the expense of longer processing times.
                    * 0: no resilience
                    * 1: light resilience
                    * 2: heavy resilience
                    * 3: even heavier resilience
                    If ``None``, level 0 will be chosen as default.

            max_time: (EXPERIMENTAL setting, can break between releases without warning)
                Maximum amount of time, a runtime session can be open before being
                forcibly closed. Can be specified as seconds (int) or a string like "2h 30m 40s".

        Raises:
            IBMInputValueError: If an input value is invalid.
        """
        super().__init__(
            circuits=circuits if isinstance(circuits, Iterable) else [circuits],
            parameters=parameters,
        )
        self._skip_transpilation = skip_transpilation
        if not service:
            # try to initialize service with default saved account
            service = QiskitRuntimeService()
        self._service = service
        if isinstance(options, dict) and "backend" in options:
            backend = options.get("backend")
            if isinstance(backend, IBMBackend):
                del options["backend"]
                options["backend_name"] = backend.name
            elif isinstance(backend, str):
                del options["backend"]
                options["backend_name"] = backend
            else:
                raise IBMInputValueError(
                    "'backend' property in 'options' should be either the string name of the "
                    "backend or an instance of 'IBMBackend' class"
                )
        inputs = {
            "circuits": circuits,
            "parameters": parameters,
            "skip_transpilation": self._skip_transpilation,
        }
        if transpilation_settings:
            inputs.update({"transpilation_settings": transpilation_settings})
        if resilience_settings:
            inputs.update({"resilience_settings": resilience_settings})
        self._session = RuntimeSession(
            service=self._service,
            program_id="sampler",
            inputs=inputs,
            options=options,
            max_time=self.calculate_max_time(max_time=max_time),
        )

    def calculate_max_time(self, max_time: Optional[Union[int, str]] = None) -> int:
        """Calculate max_time in seconds from hour minute seconds string. Ex: 2h 30m 40s"""
        try:
            return hms_to_seconds(max_time) if isinstance(max_time, str) else max_time
        except IBMInputValueError as input_value_error:
            raise IBMInputValueError(
                "Invalid value given for max_time.", input_value_error.message
            )

    def _call(
        self,
        circuits: Sequence[int],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> SamplerResult:
        """Calculates probabilities or quasi-probabilities for given inputs in a runtime session.

        Args:
            circuits: A list of circuit indices.
            parameter_values: An optional list of concrete parameters to be bound.
            **run_options: A collection of kwargs passed to `backend.run()`.

        Returns:
            An instance of :class:`qiskit.primitives.SamplerResult`.
        """
        self._session.write(
            circuit_indices=circuits,
            parameter_values=parameter_values,
            run_options=run_options,
        )
        raw_result = self._session.read()
        return SamplerResult(
            quasi_dists=raw_result["quasi_dists"],
            metadata=raw_result["metadata"],
        )

    def close(self) -> None:
        """Close the session and free resources"""
        self._session.close()
