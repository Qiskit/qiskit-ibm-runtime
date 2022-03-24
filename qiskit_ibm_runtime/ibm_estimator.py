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

"""Qiskit Runtime Estimator primitive service."""

from typing import Iterable, Optional, Union

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import SparsePauliOp

from .base_primitive import BasePrimitive
from .estimator import Estimator


class IBMEstimator(BasePrimitive):
    """Class for interacting with Qiskit Runtime Estimator primitive service.

    Qiskit Runtime Estimator primitive service estimates expectation values of quantum circuits and
    observables.

    IBMEstimator can be initialized with the following parameters. It returns a factory.

    * service: Optional instance of :class:`qiskit_ibm_runtime.IBMRuntimeService` class,
        defaults to `IBMRuntimeService()` which tries to initialize your default saved account.

    * backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
        string name of backend, if not specified a backend will be selected automatically
        (IBM Cloud only).

    The factory can then be called with the following parameters to initialize the Estimator
    primitive. It returns an :class:`qiskit_ibm_runtime.sessions.EstimatorSession` instance.

    * circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
        a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

    * observables: a list of :class:`~qiskit.quantum_info.SparsePauliOp`.

    * parameters: a list of parameters of the quantum circuits.
        (:class:`~qiskit.circuit.parametertable.ParameterView` or
        a list of :class:`~qiskit.circuit.Parameter`) specifying the order
        in which parameter values will be bound.

    The :class:`qiskit_ibm_runtime.sessions.EstimatorSession` instance can be called repeatedly
    with the following parameters to estimate expectation values.

    * circuit_indices: A list of circuit indices.

    * observable_indices: A list of observable indices.

    * parameter_values: An optional list of concrete parameters to be bound.

    All the above lists should be of the same length.

    Example::

        from qiskit.circuit.library import RealAmplitudes
        from qiskit.quantum_info import SparsePauliOp

        from qiskit_ibm_runtime import IBMRuntimeService, IBMEstimator

        service = IBMRuntimeService(auth="cloud")
        estimator_factory = IBMEstimator(service=service, backend="ibmq_qasm_simulator")

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with estimator_factory([psi1, psi2], [H1, H2, H3]) as estimator:
            theta1 = [0, 1, 1, 2, 3, 5]
            theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
            theta3 = [1, 2, 3, 4, 5, 6]

            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            psi1_H1_result = estimator([0], [0], [theta1])
            print(psi1_H1_result)

            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            psi1_H23_result = estimator([0, 0], [1, 2], [theta1]*2)
            print(psi1_H23_result)

            # calculate [ <psi2(theta2)|H2|psi2(theta2)> ]
            psi2_H2_result = estimator([1], [1], [theta2])
            print(psi2_H2_result)

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>, <psi1(theta3)|H1|psi1(theta3)> ]
            psi1_H1_result2 = estimator([0, 0], [0, 0], [theta1, theta3])
            print(psi1_H1_result2)

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>,
            #             <psi2(theta2)|H2|psi2(theta2)>,
            #             <psi1(theta3)|H3|psi1(theta3)> ]
            psi12_H23_result = estimator([0, 1, 0], [0, 1, 2], [theta1, theta2, theta3])
            print(psi12_H23_result)
    """

    def __call__(  # type: ignore[override]
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        observables: Iterable[SparsePauliOp],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        skip_transpilation: bool = False,
    ) -> Estimator:
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

        Returns:
            An instance of :class:`qiskit_ibm_runtime.estimator.Estimator`.
        """
        # pylint: disable=arguments-differ
        return Estimator(
            circuits=circuits,
            observables=observables,
            parameters=parameters,
            skip_transpilation=skip_transpilation,
            service=self._service,
            backend_name=self._backend_name,
        )
