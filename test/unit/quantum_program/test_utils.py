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
from qiskit.circuit.library import U2Gate
from qiskit.quantum_info import Operator

from qiskit_ibm_runtime.quantum_program.utils import remove_parameter_expressions

from ...ibm_test_case import IBMTestCase


class TestRemoveParameterExpressions(IBMTestCase):
    """Test the function :func:`~remove_parameter_expressions`."""

    def test_remove_parameter_expressions_static_circuit(self):
        """
        Test the function :func:`~remove_parameter_expressions` for static circuits.
        The static property allows a rigorous check using operator equivalence.
        """
        p1 = Parameter("p1")
        p2 = Parameter("p2")
        param_values = np.array([[[1, 2], [3, 4], [5, 6], [7, 8]], [[9, 10], [11, 12], [13, 14], [15, 16]], [[17, 18], [19, 20], [21, 22], [23, 24]]])

        circ = QuantumCircuit(2)
        circ.h(0)
        circ.rz(p1, 0)
        circ.rx(p1 + p2, 1)
        circ.rx(p1 + p2, 0)
        circ.append(U2Gate(p1 - p2, p1 + p2), [1])

        new_circ, new_values = remove_parameter_expressions(circ, param_values)

        self.assertEqual(len(new_circ.parameters), 3)

        self.assertEqual(param_values.shape[:-1], new_values.shape[:-1])
        param_values_flat = param_values.reshape(-1, param_values.shape[-1])
        new_values_flat = new_values.reshape(-1, new_values.shape[-1])
        for param_set_1, param_set_2 in zip(param_values_flat, new_values_flat):
            self.assertTrue(
                Operator.from_circuit(circ.assign_parameters(param_set_1)).equiv(
                    Operator.from_circuit(new_circ.assign_parameters(param_set_2))
                )
            )

    def test_remove_parameter_expressions_dynamic_circuit(self):
        """
        Test the function :func:`~remove_parameter_expressions` for dynamic circuits.
        """
        p1 = Parameter("p1")
        p2 = Parameter("p2")
        param_values = np.array([[[1, 2], [3, 4], [5, 6], [7, 8]], [[9, 10], [11, 12], [13, 14], [15, 16]], [[17, 18], [19, 20], [21, 22], [23, 24]]])
        param_values_flat = param_values.reshape(-1, param_values.shape[-1])

        circ = QuantumCircuit(2, 1)
        circ.h(0)
        circ.rz(p1, 0)
        with circ.box():
            circ.rx(p1 + p2, 1)
            circ.append(U2Gate(p1 - p2, p1 + p2), [1])
            circ.rz(p1, 1)
        circ.rx(p1 + p2, 0)
        circ.measure(0, 0)
        with circ.if_test((0, 1)):
            with circ.if_test((0, 0)) as else_:
                circ.h(0)
            with else_:
                circ.rz(p1 + 3, 0)
        circ.rx(p1 * p2, 1)

        new_circ, new_values = remove_parameter_expressions(circ, param_values)

        # parameter names: 3 + p1, p1, p1 + p2, p1 - p2, p1*p2
        self.assertEqual(len(new_circ.parameters), 5)
        self.assertEqual(param_values.shape[:-1], new_values.shape[:-1])

        outer_circ_1 = QuantumCircuit(2)
        outer_circ_1.data = [circ.data[i] for i in (0, 1, 3, 6)]
        outer_circ_2 = QuantumCircuit(2)
        outer_circ_2.data = [new_circ.data[i] for i in (0, 1, 3, 6)]

        outer_params_2 = new_values[..., [0, 1, 4]]
        outer_2_flat = outer_params_2.reshape(-1, outer_params_2.shape[-1])
        for param_set_1, param_set_2 in zip(param_values_flat, outer_2_flat):
            self.assertTrue(
                Operator.from_circuit(outer_circ_1.assign_parameters(param_set_1)).equiv(
                    Operator.from_circuit(outer_circ_2.assign_parameters(param_set_2))
                )
            )

        self.assertEqual(new_circ.data[2].operation.name, "box")
        box_circ_1 = QuantumCircuit(2)
        box_circ_1.data = circ.data[2].operation.blocks[0]
        box_circ_2 = QuantumCircuit(2)
        box_circ_2.data = new_circ.data[2].operation.blocks[0]        

        box_params_2 = new_values[..., [0, 1, 2]]
        box_2_flat = box_params_2.reshape(-1, box_params_2.shape[-1])
        for param_set_1, param_set_2 in zip(param_values_flat, box_2_flat):
            self.assertTrue(
                Operator.from_circuit(box_circ_1.assign_parameters(param_set_1)).equiv(
                    Operator.from_circuit(box_circ_2.assign_parameters(param_set_2))
                )
            )

        self.assertEqual(new_circ.data[5].operation.name, "if_else")
        self.assertEqual(new_circ.data[5].operation.blocks[0].data[0].operation.name, "if_else")
        if_circ_1 = circ.data[5].operation.blocks[0].data[0].operation.blocks[0]
        if_circ_2 = new_circ.data[5].operation.blocks[0].data[0].operation.blocks[0]

        self.assertTrue(
            Operator.from_circuit(if_circ_1).equiv(
                Operator.from_circuit(if_circ_2)
            )
        )

        else_circ_1 = circ.data[5].operation.blocks[0].data[0].operation.blocks[1]
        else_circ_2 = new_circ.data[5].operation.blocks[0].data[0].operation.blocks[1]

        else_1_flat = param_values_flat[:, 0]
        else_2_flat = new_values[..., 3].ravel()
        for param_set_1, param_set_2 in zip(else_1_flat, else_2_flat):
            self.assertTrue(
                Operator.from_circuit(else_circ_1.assign_parameters([param_set_1])).equiv(
                    Operator.from_circuit(else_circ_2.assign_parameters([param_set_2]))
                )
            )