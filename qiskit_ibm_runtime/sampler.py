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
    calculate probabilites or quasi-probabilities.

    * circuit_indices: A list of circuit indices.

    * parameter_values: An optional list of concrete parameters to be bound.

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
            result = sampler(circuit_indices=[0], parameter_values=[[]])
            print(result)

        # executes three Bell circuits
        with Sampler(circuits=[bell]*3, service=service, options=options) as sampler:
            result = sampler(circuit_indices=[0, 1, 2], parameter_values=[[]]*3)
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
            result = sampler(circuit_indices=[0, 0, 1], parameter_values=[theta1, theta2, theta3])
            print(result)
    """

    def __init__(
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        skip_transpilation: Optional[bool] = False,
        service: Optional[QiskitRuntimeService] = None,
        options: Optional[Dict] = None,
    ):
        """Initializes the Sampler primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameters: A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`).
            skip_transpilation: Transpilation is skipped if set to True.
                False by default.
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
        self._session = RuntimeSession(
            service=self._service,
            program_id="sampler",
            inputs=inputs,
            options=options,
        )

    def __call__(
        self,
        circuit_indices: Sequence[int],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> SamplerResult:
        """Calculates probabilites or quasi-probabilities for given inputs in a runtime session.

        Args:
            circuit_indices: A list of circuit indices.
            parameter_values: An optional list of concrete parameters to be bound.
            **run_options: A collection of kwargs passed to `backend.run()`.

        Returns:
            An instance of :class:`qiskit.primitives.SamplerResult`.
        """
        self._session.write(
            circuit_indices=circuit_indices,
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
