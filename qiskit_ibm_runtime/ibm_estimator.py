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

from typing import List, Tuple, Optional, Union, Dict

from qiskit.circuit import QuantumCircuit

# TODO uncomment when importing Group from terra
# from qiskit.primitives.base_estimator import Group
from qiskit.quantum_info import SparsePauliOp

from .base_primitive import BasePrimitive

# TODO remove Group when importing from terra
from .sessions.estimator_session import EstimatorSession, Group


class IBMEstimator(BasePrimitive):
    """Class for interacting with Qiskit Runtime Estimator primitive service.

    Qiskit Runtime Estimator primitive service estimates expectation values of quantum circuits and
    observables.

    Example::

        from qiskit.circuit.library import RealAmplitudes
        from qiskit.quantum_info import SparsePauliOp

        from qiskit_ibm_runtime import IBMRuntimeService, IBMEstimator

        service = IBMRuntimeService(auth="cloud")
        estimator = IBMEstimator(service=service, backend="ibmq_qasm_simulator")

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        params1 = psi1.parameters
        params2 = psi2.parameters

        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with estimator([psi1, psi2], [H1, H2, H3], [params1, params2]) as session:
            theta1 = [0, 1, 1, 2, 3, 5]
            theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
            theta3 = [1, 2, 3, 4, 5, 6]

            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            psi1_H1_result = session([0], [0], [theta1])
            print(psi1_H1_result)

            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            psi1_H23_result = session([0, 0], [1, 2], [theta1]*2)
            print(psi1_H23_result)

            # calculate [ <psi2(theta2)|H2|psi2(theta2)> ]
            psi2_H2_result = session([1], [1], [theta2])
            print(psi2_H2_result)

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>, <psi1(theta3)|H1|psi1(theta3)> ]
            psi1_H1_result2 = session([0, 0], [0, 0], [theta1, theta3])
            print(psi1_H1_result2)

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>,
            #             <psi2(theta2)|H2|psi2(theta2)>,
            #             <psi1(theta3)|H3|psi1(theta3)> ]
            psi12_H23_result = session([0, 0, 0], [0, 1, 2], [theta1, theta2, theta3])
            print(psi12_H23_result)
    """

    def __call__(  # type: ignore[override]
        self,
        circuits: List[QuantumCircuit],
        observables: List[SparsePauliOp],
        grouping: Optional[List[Union[Group, Tuple[int, int]]]] = None,
        transpile_options: Optional[Dict] = None,
    ) -> EstimatorSession:
        # pylint: disable=arguments-differ
        inputs = {
            "circuits": circuits,
            "observables": observables,
            "grouping": grouping,
            "transpile_options": transpile_options,
        }

        options = {}
        if self._backend:
            options["backend_name"] = self._backend

        return EstimatorSession(
            runtime=self._service,
            program_id="estimator",
            inputs=inputs,
            options=options,
        )
