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

from typing import Tuple, Optional, Union, List
from math import pi
from operator import mod

from qiskit.converters import dag_to_circuit, circuit_to_dag
from qiskit.circuit.library.standard_gates import RZZGate, RZGate, XGate, GlobalPhaseGate, RXGate
from qiskit.circuit.parameterexpression import ParameterExpression
from qiskit.circuit import Qubit, ControlFlowOp
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import Target
from qiskit.transpiler.basepasses import TransformationPass

import numpy as np


class FoldRzzAngle(TransformationPass):
    """Fold Rzz gate angle into calibrated range of 0-pi/2 with
    local gate tweaks.

    In the IBM Quantum ISA, the instruction Rzz(theta) has
    valid "theta" value of [0, pi/2] and any instruction outside
    this range becomes a non-ISA operation for the quantum backend.
    The transpiler pass discovers such non-ISA Rzz gates
    and folds the gate angle into the calibrated range
    with addition of single qubit gates while preserving
    logical equivalency of the input quantum circuit.
    Added local gates might be efficiently merged into
    neighboring single qubit gates by the following single qubit
    optimization passes.

    This pass allows the Qiskit users to naively use the Rzz gates
    with angle of arbitrary real numbers.
    """

    def __init__(self, target: Optional[Union[Target, List[str]]] = None):
        """
        Args:
            target - either a target or only a list of basis gates, either way it can be checked
            if an instruction is supported using the `in` operator, for example `"rx" in target`.
            If None then we assume that there is no limit on the gates in the transpiled circuit.
        """
        super().__init__()
        if target is None:
            self._target = ["rz", "x", "rx", "rzz"]
        else:
            self._target = target

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        self._run_inner(dag)
        return dag

    def _run_inner(self, dag: DAGCircuit) -> bool:
        """Mutate the input dag to fix non-ISA Rzz angles.
        Return true if the dag was modified."""
        modified = False
        for node in dag.op_nodes():
            if isinstance(node.op, ControlFlowOp):
                modified_blocks = False
                new_blocks = []
                for block in node.op.blocks:
                    block_dag = circuit_to_dag(block)
                    if self._run_inner(block_dag):
                        # Store circuit with Rzz modification
                        new_blocks.append(dag_to_circuit(block_dag))
                        modified_blocks = True
                    else:
                        # Keep original circuit to save memory
                        new_blocks.append(block)
                if modified_blocks:
                    dag.substitute_node(
                        node,
                        node.op.replace_blocks(new_blocks),
                        inplace=True,
                    )
                    modified = True
                continue

            if not isinstance(node.op, RZZGate):
                continue

            angle = node.op.params[0]

            if not isinstance(angle, ParameterExpression) and 0 <= angle <= pi / 2:
                # Angle is an unbound parameter or a calibrated value.
                continue

            # Modify circuit around Rzz gate to address non-ISA angles.
            if isinstance(angle, ParameterExpression):
                replace = self._unbounded_parameter(angle, node.qargs)
            else:
                replace = self._numeric_parameter(angle, node.qargs)

            if replace is not None:
                dag.substitute_node_with_dag(node, replace)
                modified = True

        return modified

    # The next function is required because sympy doesn't convert Boolean values to integers.
    # symengine maybe does but I failed to find it in its documentation.
    def gteq_op(self, exp1: ParameterExpression, exp2: ParameterExpression) -> ParameterExpression:
        """Return an expression which, after substitution, will be equal to 1 if `exp1` is
        greater or equal than `exp2`, and 0 otherwise"""
        tmp = (exp1 - exp2).sign()

        # We want to return 1 if tmp is 1 or 0, and 0 otherwise
        return ((tmp + 0.1).sign() + 1) / 2

    def _unbounded_parameter(
        self, angle: ParameterExpression, qubits: Tuple[Qubit, ...]
    ) -> DAGCircuit:
        if "rz" not in self._target or "rx" not in self._target or "rzz" not in self._target:
            return None

        global_phase = (
            (-pi / 2) * self.gteq_op((angle + pi / 2)._apply_operation(mod, 2 * pi), pi)
            + pi * self.gteq_op(angle._apply_operation(mod, 2 * pi), 3 * pi / 2)
            + pi * self.gteq_op((angle + pi)._apply_operation(mod, 4 * pi), 2 * pi)
        )
        rz_angle = pi * self.gteq_op((angle + pi / 2)._apply_operation(mod, 2 * pi), pi)
        rx_angle = pi * self.gteq_op(angle._apply_operation(mod, pi), pi / 2)
        rzz_angle = pi / 2 - (angle._apply_operation(mod, pi) - pi / 2).abs()

        new_dag = DAGCircuit()
        new_dag.add_qubits(qubits=qubits)
        new_dag.apply_operation_back(GlobalPhaseGate(global_phase))
        new_dag.apply_operation_back(
            RZGate(rz_angle),
            qargs=(qubits[0],),
            check=False,
        )
        new_dag.apply_operation_back(
            RZGate(rz_angle),
            qargs=(qubits[1],),
            check=False,
        )
        new_dag.apply_operation_back(
            RXGate(rx_angle),
            qargs=(qubits[0],),
            check=False,
        )
        new_dag.apply_operation_back(
            RZZGate(rzz_angle),
            qargs=qubits,
            check=False,
        )
        new_dag.apply_operation_back(
            RXGate(rx_angle),
            qargs=(qubits[0],),
            check=False,
        )

        return new_dag

    def _numeric_parameter(self, angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
        wrap_angle = np.angle(np.exp(1j * angle))
        if 0 <= wrap_angle <= pi / 2:
            # In the first quadrant.
            replace = self._quad1(wrap_angle, qubits)
        elif pi / 2 < wrap_angle <= pi:
            # In the second quadrant.
            replace = self._quad2(wrap_angle, qubits)
        elif -pi <= wrap_angle <= -pi / 2:
            # In the third quadrant.
            replace = self._quad3(wrap_angle, qubits)
        elif -pi / 2 < wrap_angle < 0:
            # In the forth quadrant.
            replace = self._quad4(wrap_angle, qubits)
        else:
            raise RuntimeError("Unreacheable.")
        if pi < angle % (4 * pi) < 3 * pi:
            replace.apply_operation_back(GlobalPhaseGate(pi))

        return replace

    def _quad1(self, angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
        """Handle angle between [0, pi/2].

        Circuit is not transformed - the Rzz gate is calibrated for the angle.

        Returns:
            A new dag with the same Rzz gate.
        """
        if "rzz" not in self._target:
            return None

        new_dag = DAGCircuit()
        new_dag.add_qubits(qubits=qubits)
        new_dag.apply_operation_back(
            RZZGate(angle),
            qargs=qubits,
            check=False,
        )
        return new_dag

    def _quad2(self, angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
        """Handle angle between (pi/2, pi].

        Circuit is transformed into the following form:

                 ┌───────┐┌───┐            ┌───┐
            q_0: ┤ Rz(π) ├┤ X ├─■──────────┤ X ├
                 ├───────┤└───┘ │ZZ(π - θ) └───┘
            q_1: ┤ Rz(π) ├──────■───────────────
                 └───────┘

        Returns:
            New dag to replace Rzz gate.
        """
        if "rz" not in self._target or "x" not in self._target or "rzz" not in self._target:
            return None

        new_dag = DAGCircuit()
        new_dag.add_qubits(qubits=qubits)
        new_dag.apply_operation_back(GlobalPhaseGate(pi / 2))
        new_dag.apply_operation_back(
            RZGate(pi),
            qargs=(qubits[0],),
            cargs=(),
            check=False,
        )
        new_dag.apply_operation_back(
            RZGate(pi),
            qargs=(qubits[1],),
            check=False,
        )
        if not np.isclose(new_angle := (pi - angle), 0.0):
            new_dag.apply_operation_back(
                XGate(),
                qargs=(qubits[0],),
                check=False,
            )
            new_dag.apply_operation_back(
                RZZGate(new_angle),
                qargs=qubits,
                check=False,
            )
            new_dag.apply_operation_back(
                XGate(),
                qargs=(qubits[0],),
                check=False,
            )
        return new_dag

    def _quad3(self, angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
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
        if "rz" not in self._target or "rzz" not in self._target:
            return None

        new_dag = DAGCircuit()
        new_dag.add_qubits(qubits=qubits)
        new_dag.apply_operation_back(GlobalPhaseGate(-pi / 2))
        new_dag.apply_operation_back(
            RZGate(pi),
            qargs=(qubits[0],),
            check=False,
        )
        new_dag.apply_operation_back(
            RZGate(pi),
            qargs=(qubits[1],),
            check=False,
        )
        if not np.isclose(new_angle := (pi - np.abs(angle)), 0.0):
            new_dag.apply_operation_back(
                RZZGate(new_angle),
                qargs=qubits,
                check=False,
            )
        return new_dag

    def _quad4(self, angle: float, qubits: Tuple[Qubit, ...]) -> DAGCircuit:
        """Handle angle between (-pi/2, 0).

        Circuit is transformed into following form:

                 ┌───┐             ┌───┐
            q_0: ┤ X ├─■───────────┤ X ├
                 └───┘ │ZZ(Abs(θ)) └───┘
            q_1: ──────■────────────────

        Returns:
            New dag to replace Rzz gate.
        """
        if "x" not in self._target or "rzz" not in self._target:
            return None

        new_dag = DAGCircuit()
        new_dag.add_qubits(qubits=qubits)
        new_dag.apply_operation_back(
            XGate(),
            qargs=(qubits[0],),
            check=False,
        )
        new_dag.apply_operation_back(
            RZZGate(abs(angle)),
            qargs=qubits,
            check=False,
        )
        new_dag.apply_operation_back(
            XGate(),
            qargs=(qubits[0],),
            check=False,
        )
        return new_dag
