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
"""
Utility functions for primitives
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TypeVar
from qiskit.circuit import QuantumCircuit


T = TypeVar("T")  # pylint: disable=invalid-name


def _finditer(obj: T, objects: list[T]) -> Iterator[int]:
    """Return an iterator yielding the indices matching obj."""
    return map(lambda x: x[0], filter(lambda x: x[1] == obj, enumerate(objects)))


def _circuit_key(circuit: QuantumCircuit) -> tuple:
    """Private key function for QuantumCircuit.
    This is the workaround until :meth:`QuantumCircuit.__hash__` will be introduced.
    If key collision is found, please add elements to avoid it.
    Args:
        circuit: Input quantum circuit.
    Returns:
        Key for directory.
    """
    return (
        id(circuit),
        circuit.num_qubits,
        circuit.num_clbits,
        circuit.num_parameters,
        tuple(
            (d.qubits, d.clbits, d.operation.name, tuple(d.operation.params))
            for d in circuit.data
        ),
        None if circuit._op_start_times is None else tuple(circuit._op_start_times),
    )
