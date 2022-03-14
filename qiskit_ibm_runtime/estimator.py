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

"""Estimator primitive."""

from typing import Iterable, Optional, Dict, Sequence, Any, Union

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import SparsePauliOp

# TODO import BaseEstimator and EstimatorResult from terra once released
from .qiskit.primitives import BaseEstimator, EstimatorResult
from .ibm_runtime_service import IBMRuntimeService
from .runtime_session import RuntimeSession


class Estimator(BaseEstimator):
    """Estimator primitive."""

    def __init__(
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        observables: Iterable[SparsePauliOp],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        skip_transpilation: Optional[bool] = False,
        service: Optional[IBMRuntimeService] = None,
        backend_name: Optional[str] = None,
    ):
        """Initializes the Estimator primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            observables: a list of :class:`~qiskit.quantum_info.SparsePauliOp`
            parameters: a list of parameters of the quantum circuits.
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`) specifying the order
                in which parameter values will be bound.
            skip_transpilation: Transpilation is skipped if set to True.
                False by default.
            service: Optional instance of :class:`qiskit_ibm_runtime.IBMRuntimeService` class,
                defaults to `IBMRuntimeService()` which tries to initialize your default saved
                account.
            backend_name: Optional string name of backend (if not specified a backend will be
                selected automatically on IBM Cloud only).
        """
        super().__init__(
            circuits=circuits,
            observables=observables,
            parameters=parameters,
        )
        self._skip_transpilation = skip_transpilation
        self._service = service
        self._backend_name = backend_name
        options = {}
        if self._backend_name:
            options["backend_name"] = self._backend_name
        inputs = {
            "circuits": circuits,
            "observables": observables,
            "parameters": parameters,
            "skip_transpilation": self._skip_transpilation,
        }
        self._session = RuntimeSession(
            runtime=self._service,
            program_id="estimator",
            inputs=inputs,
            options=options,
        )

    def __call__(
        self,
        circuit_indices: Sequence[int],
        observable_indices: Sequence[int],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> EstimatorResult:
        """Estimates expectation values for given inputs in a runtime session.

        Args:
            circuit_indices: A list of circuit indices.
            observable_indices: A list of observable indices.
            parameter_values: An optional list of concrete parameters to be bound.
            **run_options: A collection of kwargs passed to `backend.run()`.

        Returns:
            An instance of :class:`qiskit.primitives.EstimatorResult`.
        """
        self._session.write(
            circuit_indices=circuit_indices,
            observable_indices=observable_indices,
            parameter_values=parameter_values,
            run_options=run_options,
        )
        raw_result = self._session.read()
        return EstimatorResult(
            values=raw_result["values"],
            metadata=raw_result["metadata"],
        )

    def close(self) -> None:
        """Close the session and free resources"""
        self._session.close()
