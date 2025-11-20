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


def _replace_parameter_expressions(
    circuit: QuantumCircuit,
    parameter_table: ParameterExpressionTable,
    parameter_expressions_to_new_parameters_map: dict[ParameterExpression, Parameter]
) -> QuantumCircuit:
    new_circuit = circuit.copy_empty_like()
    new_data = []

    for instruction in circuit.data:
        if instruction.is_control_flow():
            new_blocks = [
                _replace_parameter_expressions(block, parameter_table, parameter_expressions_to_new_parameters_map)
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
            if param_exp in parameter_expressions_to_new_parameters_map:
                new_param = parameter_expressions_to_new_parameters_map[param_exp]
            else:
                if isinstance(param_exp, Parameter):
                    new_param = param_exp               
                else:
                    new_param = Parameter(str(param_exp))
                parameter_table.append(param_exp)
                parameter_expressions_to_new_parameters_map[param_exp] = new_param
            new_op_params.append(new_param)

        new_gate = instruction.operation.copy()
        new_gate.params = new_op_params
        new_data.append(instruction.replace(params=new_op_params, operation=new_gate))

    new_circuit.data = new_data
    return new_circuit


def replace_parameter_expressions(
    circuit: QuantumCircuit, parameter_values: np.ndarray
) -> tuple[QuantumCircuit, np.ndarray]:
     """
     A helper to replace a circuit's parameter expressions with parameters.

     The function tranverses the circuit and collects all the parameters and parameter expressions.
     A new parameter is created for every parameter expression that is not a parameter.
     The function builds a new circuit, where each parameter expression is replaced by the
     corresponding new parameter.
     In addition, the function creates a new array of parameter values, which matches the parameters
     of the new circuit. Values for new parameters are obtained by evaluating the original
     expressions over the original parameter values.
     
     Example:

        .. code-block:: python

            import numpy as np
            from qiskit.circuit import QuantumCircuit, Parameter
            from qiskit_ibm_runtime.quantum_program.utils import replace_parameter_expressions

            circuit = QuantumCircuit(1)
            circuit.rx(a := Parameter("a"), 0)
            circuit.rx(b := Parameter("b"), 0)
            circuit.rx(a + b, 0)

            values = np.array([[1, 2], [3, 4]])

            # ``new_circuit`` will incorporate a new parameter, which replaces the parameter
            # expression ``a + b``
            # ``new_values`` will be ``np.array([[1, 2, 3], [3, 4, 7]])``
            new_circuit, new_values = replace_parameter_expressions(circuit, values)
     """
    parameter_table = ParameterExpressionTable()
    parameter_expressions_to_new_parameters_map: dict[ParameterExpression, Parameter] = {}

    new_circuit = _replace_parameter_expressions(circuit, parameter_table, parameter_expressions_to_new_parameters_map)

    new_values = np.zeros(parameter_values.shape[:-1] + (len(new_circuit.parameters),))
    for idx in np.ndindex(parameter_values.shape[:-1]):
        new_values[idx] = parameter_table.evaluate(parameter_values[*idx, :])

    return new_circuit, new_values
