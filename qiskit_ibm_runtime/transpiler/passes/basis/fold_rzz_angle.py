# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Pass to wrap Rzz gate angle in calibrated range of 0-pi/2."""

from typing import Tuple
from math import pi

from qiskit.circuit.library.standard_gates import RZZGate, RZGate, XGate
from qiskit.circuit.parameterexpression import ParameterExpression
from qiskit.circuit import Qubit
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

import numpy as np


class FoldRzzAngle(TransformationPass):
    """Fold Rzz gate angle into calibrated range of 0-pi/2 with
    local gate tweaks.

    This pass preserves the number of Rzz gates, but it may add
    extra single qubit gate operations.
    These gates might be reduced by the following
    single qubit optimization passes.
    """

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        # Currently control flow ops and Rzz cannot live in the same circuit.
        # Once it's supported, we need to recursively check subroutines.
        for node in dag.op_nodes():
            if not isinstance(node.op, RZZGate):
                continue
            angle = node.op.params[0]
            if isinstance(angle, ParameterExpression) or 0 <= angle <= pi / 2:
                # Angle is unbound parameter or calibrated value.
                continue
            wrap_angle = np.angle(np.exp(1j * angle))
            if 0 <= wrap_angle <= pi / 2:
                # In the first quadrant after phase wrapping.
                # We just need to remove 2pi offset.
                dag.substitute_node(
                    node,
                    RZZGate(wrap_angle),
                    inplace=True,
                )
                continue
            elif pi /2 < wrap_angle <= pi:
                # In the second quadrant.
                replace = _quad2(wrap_angle, node.qargs)
            elif -pi <= wrap_angle <= - pi / 2:
                # In the third quadrant.
                replace = _quad3(wrap_angle, node.qargs)
            elif -pi / 2 < wrap_angle < 0:
                # In the forth quadrant.
                 replace = _quad4(wrap_angle, node.qargs)
            dag.substitute_node_with_dag(node, replace)
        return dag


def _quad2(angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
    """Handle angle between (pi/2, pi].

    Circuit is transformed into following form:

             ┌───────┐┌───┐            ┌───┐
        q_0: ┤ Rz(π) ├┤ X ├─■──────────┤ X ├
             ├───────┤└───┘ │ZZ(π - θ) └───┘
        q_1: ┤ Rz(π) ├──────■───────────────
             └───────┘

    Returns:
        New dag to replace Rzz gate.
    """
    new_dag = DAGCircuit()
    new_dag.add_qubits(qubits=qubits)
    new_dag.apply_operation_back(
        RZGate(pi),
        qargs=(qubits[0],),
        cargs=(),
        check=False,
    )
    new_dag.apply_operation_back(
        RZGate(pi),
        qargs=(qubits[1],),
        cargs=(),
        check=False,
    )
    if not np.isclose(new_angle := (pi - angle), 0.0):
        new_dag.apply_operation_back(
            XGate(),
            qargs=(qubits[0],),
            cargs=(),
            check=False,
        )
        new_dag.apply_operation_back(
            RZZGate(new_angle),
            qargs=qubits,
            cargs=(),
            check=False,
        )
        new_dag.apply_operation_back(
            XGate(),
            qargs=(qubits[0],),
            cargs=(),
            check=False,
        )
    return new_dag


def _quad3(angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
    """Handle angle between [-pi, -pi/2].

    Circuit is transformed into following form:

             ┌───────┐
        q_0: ┤ Rz(π) ├─■───────────────
             ├───────┤ │ZZ(π - Abs(θ))
        q_1: ┤ Rz(π) ├─■───────────────
             └───────┘

    Returns:
        New dag to replace Rzz gate.
    """
    new_dag = DAGCircuit()
    new_dag.add_qubits(qubits=qubits)
    new_dag.apply_operation_back(
        RZGate(pi),
        qargs=(qubits[0],),
        cargs=(),
        check=False,
    )
    new_dag.apply_operation_back(
        RZGate(pi),
        qargs=(qubits[1],),
        cargs=(),
        check=False,
    )
    if not np.isclose(new_angle := (pi - np.abs(angle)), 0.0):
        new_dag.apply_operation_back(
            RZZGate(new_angle),
            qargs=qubits,
            cargs=(),
            check=False,
        )
    return new_dag


def _quad4(angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
    """Handle angle between (-pi/2, 0).

    Circuit is transformed into following form:

             ┌───┐             ┌───┐
        q_0: ┤ X ├─■───────────┤ X ├
             └───┘ │ZZ(Abs(θ)) └───┘
        q_1: ──────■────────────────

    Returns:
        New dag to replace Rzz gate.
    """
    new_dag = DAGCircuit()
    new_dag.add_qubits(qubits=qubits)
    new_dag.apply_operation_back(
        XGate(),
        qargs=(qubits[0],),
        cargs=(),
        check=False,
    )
    new_dag.apply_operation_back(
        RZZGate(abs(angle)),
        qargs=qubits,
        cargs=(),
        check=False,
    )
    new_dag.apply_operation_back(
        XGate(),
        qargs=(qubits[0],),
        cargs=(),
        check=False,
    )
    return new_dag
