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

from qiskit.circuit import Parameter, QuantumCircuit, ParameterExpression, CircuitInstruction


def remove_parameter_expressions(
    circ: QuantumCircuit, param_values: np.ndarray
) -> tuple[QuantumCircuit, np.ndarray]:
    parameter_table = {}
    new_param_value_cols = []
    new_circ = circ.copy_empty_like()
    new_data = []

    for instruction in circ.data:
        if len(instruction.operation.params) == 0 or not isinstance(
            param_exp := instruction.operation.params[0], ParameterExpression
        ):
            new_data.append(instruction)
            continue

        if str(param_exp) in parameter_table:
            new_param = parameter_table[str(param_exp)]
        else:
            param_names = [param.name for param in param_exp.parameters]
            circ_params = [param.name for param in circ.parameters]

            # col_indices is the indices of columns in the parameter value array that have to be checked
            col_indices = [
                np.where(np.array(circ_params) == param_name)[0][0] for param_name in param_names
            ]

            new_param_values = np.zeros(param_values.shape[:-1] + (1,))
            for idx in np.ndindex(param_values.shape[:-1]):
                to_bind = param_values[idx]
                new_param_values[idx] = param_exp.bind_all(dict(zip(circ.parameters, to_bind)))

            new_param_value_cols.append(new_param_values)
            new_param = Parameter(str(param_exp))
            parameter_table[str(param_exp)] = new_param

        new_gate = instruction.operation.copy()
        new_gate.params = [new_param]
        new_data.append(CircuitInstruction(new_gate, instruction.qubits))
        

    new_circ.data = new_data
    return new_circ, np.concatenate(new_param_value_cols, axis=-1)
