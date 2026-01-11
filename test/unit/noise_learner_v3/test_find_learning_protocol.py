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

"""Tests the `find_learning_protocol` function."""

from qiskit.circuit import QuantumCircuit
from samplomatic import Twirl

from qiskit_ibm_runtime.noise_learner_v3.find_learning_protocol import (
    find_learning_protocol,
)

from ...ibm_test_case import IBMTestCase


class TestFindLearningProtocol(IBMTestCase):
    """Tests the `find_learning_protocol` function."""

    def test_gate_instructions(self):
        """Test gate instructions."""
        circuit = QuantumCircuit(4)
        with circuit.box([Twirl()]):
            circuit.x(0)
            circuit.x(0)
            circuit.cx(0, 1)
            circuit.cx(2, 3)
        with circuit.box([Twirl()]):
            circuit.noop(2)
            circuit.cx(0, 1)
        with circuit.box([Twirl()]):
            circuit.cx(0, 1)
            circuit.cx(1, 2)
        with circuit.box([Twirl()]):
            circuit.rzz(0.01, 0, 1)

        protocols = [find_learning_protocol(instr) for instr in circuit]
        self.assertEqual(protocols, ["pauli_lindblad"] * 2 + [None] * 2)

    def test_measure_instructions(self):
        """Test measure instructions."""
        circuit = QuantumCircuit(4, 4)
        with circuit.box([Twirl()]):
            circuit.measure(range(4), range(4))
        with circuit.box([Twirl()]):
            circuit.measure(range(2), range(2))
        with circuit.box([Twirl()]):
            circuit.noop(range(4))
            circuit.measure(range(2), range(2))
        with circuit.box([Twirl()]):
            circuit.measure(range(2), range(2))
            circuit.measure(range(2), range(2))

        protocols = [find_learning_protocol(instr) for instr in circuit]
        self.assertEqual(protocols, ["trex"] * 2 + [None] * 2)

    def test_empty_instructions(self):
        """Test empty instructions."""
        circuit = QuantumCircuit(4)
        with circuit.box([Twirl()]):
            circuit.x(0)
        with circuit.box([Twirl()]):
            circuit.noop(2)

        protocols = [find_learning_protocol(instr) for instr in circuit]
        self.assertEqual(protocols, ["pauli_lindblad"] * 2)

    def test_mixed_instructions(self):
        """Test instructions with gates and measurements."""
        circuit = QuantumCircuit(4, 2)
        with circuit.box([Twirl()]):
            circuit.cx(0, 1)
            circuit.measure([2, 3], [0, 1])

        protocols = [find_learning_protocol(instr) for instr in circuit]
        self.assertEqual(protocols, [None])
