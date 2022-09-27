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
from qiskit.circuit.bit import Bit


T = TypeVar("T")  # pylint: disable=invalid-name


def _finditer(obj: T, objects: list[T]) -> Iterator[int]:
    """Return an iterator yielding the indices matching obj."""
    return map(lambda x: x[0], filter(lambda x: x[1] == obj, enumerate(objects)))


def _bits_key(bits: tuple[Bit, ...], circuit: QuantumCircuit) -> tuple:
    return tuple(
        (
            circuit.find_bit(bit).index,
            tuple(
                (reg[0].size, reg[0].name, reg[1])
                for reg in circuit.find_bit(bit).registers
            ),
        )
        for bit in bits
    )


def _circuit_key(circuit: QuantumCircuit, functional: bool = True) -> tuple:
    """Private key function for QuantumCircuit.
    This is the workaround until :meth:`QuantumCircuit.__hash__` will be introduced.
    If key collision is found, please add elements to avoid it.
    Args:
        circuit: Input quantum circuit.
        functional: If True, the returned key only includes functional data (i.e. execution related).
    Returns:
        Composite key for circuit.
    """
    functional_key: tuple = (
        circuit.num_qubits,
        circuit.num_clbits,
        circuit.num_parameters,
        tuple(  # circuit.data
            (
                _bits_key(data.qubits, circuit),  # qubits
                _bits_key(data.clbits, circuit),  # clbits
                data.operation.name,  # operation.name
                tuple(data.operation.params),  # operation.params
            )
            for data in circuit.data
        ),
        None if circuit._op_start_times is None else tuple(circuit._op_start_times),
    )
    if functional:
        return functional_key
    return (
        circuit.name,
        *functional_key,
    )
