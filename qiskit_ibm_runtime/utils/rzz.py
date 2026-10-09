# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utilities for folding Rzz gate angles into the calibrated range."""

from __future__ import annotations

from math import pi
from typing import TYPE_CHECKING

import numpy as np
from qiskit.circuit.library.standard_gates import GlobalPhaseGate, RZGate, RZZGate, XGate
from qiskit.dagcircuit import DAGCircuit

if TYPE_CHECKING:
    from qiskit.circuit import Qubit


def fold_rzz_angle(angle: float, qubits: tuple[Qubit, ...]) -> DAGCircuit:
    """Fold an Rzz angle into the calibrated range [0, pi/2].

    Args:
        angle: The original Rzz angle.
        qubits: The qubits on which the Rzz gate acts.

    Returns:
        A DAG circuit implementing the same unitary as the original Rzz gate.
    """
    wrap_angle = np.angle(np.exp(1j * angle))

    if 0 <= wrap_angle <= pi / 2:
        dag = build_rzz_quadrant_1(wrap_angle, qubits)
    elif pi / 2 < wrap_angle <= pi:
        dag = build_rzz_quadrant_2(wrap_angle, qubits)
    elif -pi <= wrap_angle <= -pi / 2:
        dag = build_rzz_quadrant_3(wrap_angle, qubits)
    elif -pi / 2 < wrap_angle < 0:
        dag = build_rzz_quadrant_4(wrap_angle, qubits)
    else:
        raise RuntimeError("Unreachable.")

    # Wrapping the angle into (-pi, pi] drops a number of 2*pi windings;
    # each dropped winding flips the sign of the operator
    # (Rzz(theta + 2*pi) = -Rzz(theta)).
    # Re-add that sign as a global phase of pi when an odd number of
    # windings was dropped.
    windings = round((angle - wrap_angle) / (2 * pi))
    if windings % 2:
        dag.apply_operation_back(GlobalPhaseGate(pi))

    return dag


def build_rzz_quadrant_1(angle: float, qubits: tuple[Qubit, ...]) -> DAGCircuit:
    """Build the Rzz circuit for an angle in [0, pi/2]."""
    new_dag = DAGCircuit()
    new_dag.add_qubits(qubits=qubits)
    new_dag.apply_operation_back(
        RZZGate(angle),
        qargs=qubits,
        check=False,
    )
    return new_dag


def build_rzz_quadrant_2(angle: float, qubits: tuple[Qubit, ...]) -> DAGCircuit:
    """Build the Rzz circuit for an angle in (pi/2, pi]."""
    new_dag = DAGCircuit()
    new_dag.add_qubits(qubits=qubits)
    new_dag.apply_operation_back(GlobalPhaseGate(pi / 2))
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


def build_rzz_quadrant_3(angle: float, qubits: tuple[Qubit, ...]) -> DAGCircuit:
    """Build the Rzz circuit for an angle in [-pi, -pi/2]."""
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


def build_rzz_quadrant_4(angle: float, qubits: tuple[Qubit, ...]) -> DAGCircuit:
    """Build the Rzz circuit for an angle in (-pi/2, 0)."""
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
