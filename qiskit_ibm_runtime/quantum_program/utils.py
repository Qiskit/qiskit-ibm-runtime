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

"""Util functions for the quantum program."""

from __future__ import annotations

import numpy as np

from qiskit.circuit import Parameter, QuantumCircuit, ParameterExpression

from samplomatic.samplex import ParameterExpressionTable


def _remove_parameter_expressions_in_blocks(
    circ: QuantumCircuit,
    parameter_table: ParameterExpressionTable,
    parameter_expressions_metadata: dict[ParameterExpression, tuple[Parameter, int]]
) -> QuantumCircuit:
    new_circ = circ.copy_empty_like()
    new_data = []

    for instruction in circ.data:
        if instruction.is_control_flow():
            new_blocks = [
                _remove_parameter_expressions_in_blocks(block, parameter_table, parameter_expressions_metadata)
                for block in instruction.operation.blocks
            ]
            new_gate = instruction.operation.replace_blocks(new_blocks)
            new_data.append(instruction.replace(params=new_gate.params, operation=new_gate))
            continue

        param_exps = [
            op_param
            for op_param in instruction.operation.params
            if isinstance(op_param, ParameterExpression)
        ]
        if len(param_exps) == 0:
            new_data.append(instruction)
            continue

        new_op_params = []
        for param_exp in param_exps:
            if param_exp in parameter_expressions_metadata:
                new_param = parameter_expressions_metadata[param_exp][0]
            else:
                if isinstance(param_exp, Parameter):
                    new_param = param_exp               
                else:
                    new_param = Parameter(str(param_exp))
                param_exp_index = parameter_table.append(param_exp)
                parameter_expressions_metadata[param_exp] = (new_param, param_exp_index)
            new_op_params.append(new_param)

        new_gate = instruction.operation.copy()
        new_gate.params = new_op_params
        new_data.append(instruction.replace(params=new_op_params, operation=new_gate))

    new_circ.data = new_data
    return new_circ


def remove_parameter_expressions(
    circ: QuantumCircuit, param_values: np.ndarray
) -> tuple[QuantumCircuit, np.ndarray]:
    """Create an input to the quantum program that's
    free from parameter expressions."""
    parameter_table = ParameterExpressionTable()
    parameter_expressions_metadata: dict[ParameterExpression, (Parameter, int)] = {}

    new_circ = _remove_parameter_expressions_in_blocks(circ, parameter_table, parameter_expressions_metadata)

    new_values = np.zeros(param_values.shape[:-1] + (len(new_circ.parameters),))
    for idx in np.ndindex(param_values.shape[:-1]):
        new_values[idx] = parameter_table.evaluate(param_values[*idx, :])

    return new_circ, new_values
