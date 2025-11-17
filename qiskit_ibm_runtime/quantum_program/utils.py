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


def _remove_parameter_expressions_in_blocks(
    circ: QuantumCircuit,
    param_values: np.ndarray,
    parameter_table: dict[str, Parameter],
    new_param_value_cols: list[np.ndarray],
) -> QuantumCircuit:
    new_circ = circ.copy_empty_like()
    new_data = []

    for instruction in circ.data:
        if instruction.is_control_flow():
            new_blocks = [
                _remove_parameter_expressions_in_blocks(
                    block, param_values, parameter_table, new_param_value_cols
                )
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
            if str(param_exp) in parameter_table:
                new_param = parameter_table[str(param_exp)]
            else:
                if isinstance(param_exp, Parameter):
                    location = next(
                        i for i, param in enumerate(circ.parameters) if param.name == param_exp.name
                    )
                    new_param_values = param_values[..., [location]]
                    new_param = param_exp
                else:
                    new_param_values = np.zeros(param_values.shape[:-1] + (1,))
                    for idx in np.ndindex(param_values.shape[:-1]):
                        to_bind = param_values[idx]
                        new_param_values[idx] = param_exp.bind_all(
                            dict(zip(circ.parameters, to_bind))
                        )
                    new_param = Parameter(str(param_exp))

                new_param_value_cols.append(new_param_values)
                parameter_table[str(param_exp)] = new_param

            new_op_params.append(new_param)

        new_gate = instruction.operation.copy()
        new_gate.params = new_op_params
        new_data.append(instruction.replace(params=new_op_params, operation=new_gate))

    new_circ.data = new_data
    return new_circ


def remove_parameter_expressions(
    circ: QuantumCircuit, param_values: np.ndarray
) -> tuple[QuantumCircuit, np.ndarray]:
    parameter_table: dict[str, Parameter] = {}
    new_param_value_cols: list[np.ndarray] = []

    new_circ = _remove_parameter_expressions_in_blocks(
        circ, param_values, parameter_table, new_param_value_cols
    )
    return new_circ, np.concatenate(new_param_value_cols, axis=-1)
