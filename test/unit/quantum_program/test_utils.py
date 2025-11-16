# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test utility functions of the quantum program."""

import numpy as np

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import Operator

from qiskit_ibm_runtime.quantum_program.utils import remove_parameter_expressions

from ...ibm_test_case import IBMTestCase


class TestRemoveParameterExpressions(IBMTestCase):
    """Test the function :func:`~remove_parameter_expressions`."""

    def test_remove_parameter_expressions(self):
        p1 = Parameter("p1")
        p2 = Parameter("p2")
        param_values = np.array([[[1, 2], [3, 4], [5, 6], [7, 8]], [[9, 10], [11, 12], [13, 14], [15, 16]], [[17, 18], [19, 20], [21, 22], [23, 24]]])

        circ = QuantumCircuit(2)
        circ.h(0)
        circ.rz(p1, 0)
        circ.rx(p1 + p2, 1)
        circ.rx(p1 + p2, 0)

        new_circ, new_values = remove_parameter_expressions(circ, param_values)

        self.assertEqual(len(new_circ.parameters), 2)

        self.assertEqual(param_values.shape[:-1], new_values.shape[:-1])
        param_values_flat = param_values.reshape(-1, param_values.shape[-1])
        new_values_flat = new_values.reshape(-1, param_values.shape[-1])
        for param_set_1, param_set_2 in zip(param_values_flat, new_values_flat):
            self.assertTrue(
                Operator.from_circuit(circ.assign_parameters(param_set_1)).equiv(
                    Operator.from_circuit(new_circ.assign_parameters(param_set_2))
                )
            )