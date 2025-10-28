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

"""Tests for quantum programs."""

import numpy as np
import numpy.testing as npt


from qiskit.circuit import QuantumCircuit, Parameter
from qiskit_ibm_runtime.quantum_program import (
    QuantumProgram,
    QuantumProgramResult,
    QuantumProgramItem,
)

from ..ibm_test_case import IBMTestCase


class TestQuantumProgramItem(IBMTestCase):
    """Test the QuantumProgramItem class."""

    def test_construct_simple(self):
        """Test the most simple construction."""

        circuit = QuantumCircuit(4)
        item = QuantumProgramItem(circuit)
        self.assertIs(item.circuit, circuit)

    def test_construct_params(self):
        """Test construction with a parametric circuit."""

        circuit = QuantumCircuit(5)
        circuit.rz(Parameter("a"), 0)
        circuit.rz(Parameter("b"), 1)

        circuit_arguments = np.linspace(0, 1, 20).reshape((2, 5, 2))
        item = QuantumProgramItem(circuit, circuit_arguments=circuit_arguments)
        self.assertIs(item.circuit, circuit)
        npt.assert_almost_equal(item.circuit_arguments, circuit_arguments)

    def test_construct_raises(self):
        """Test that construction raises expected errors."""

        with self.assertRaisesRegex(ValueError, "Expected.*to be a QuantumCircuit"):
            QuantumProgramItem("not a circuit")

        circuit = QuantumCircuit(5)
        circuit.rz(Parameter("a"), 0)
        with self.assertRaisesRegex(ValueError, "no 'circuit_arguments' were supplied"):
            QuantumProgramItem(circuit)

        with self.assertRaisesRegex(ValueError, "match the number of parameters"):
            QuantumProgramItem(QuantumCircuit(5), circuit_arguments=np.linspace(0, 1, 10))

        circuit = QuantumCircuit(5)
        circuit.rz(Parameter("a"), 0)
        with self.assertRaisesRegex(ValueError, "match the number of parameters"):
            QuantumProgramItem(circuit, circuit_arguments=np.linspace(0, 1, 10))


class TestQuantumProgram(IBMTestCase):
    """Test the QuantumProgram class."""

    def test_construct_empty(self):
        """Test the construction of empty programs."""

        program = QuantumProgram(10)
        self.assertEqual(program.shots, 10)
        self.assertEqual(program.items, [])

    def test_construct_nonempty(self):
        """Test the construction of nonempty programs."""

        item0 = QuantumProgramItem(QuantumCircuit(5))
        item1 = QuantumProgramItem(QuantumCircuit(2))
        program = QuantumProgram(11, [item0, item1])
        self.assertEqual(program.shots, 11)
        self.assertEqual(program.items, [item0, item1])

    def test_append(self):
        """Test the append() method."""

        program = QuantumProgram(10)
        self.assertEqual(program.items, [])

        program.append(QuantumCircuit(5))
        self.assertEqual(len(program.items), 1)
        self.assertEqual(program.items[0].circuit, QuantumCircuit(5))
        npt.assert_almost_equal(program.items[0].circuit_arguments, np.empty((0,)))

        circuit = QuantumCircuit(6)
        circuit.rz(Parameter("a"), 0)
        program.append(circuit, circuit_arguments=[10])
        self.assertEqual(len(program.items), 2)
        self.assertEqual(program.items[0].circuit, QuantumCircuit(5))
        npt.assert_almost_equal(program.items[0].circuit_arguments, np.empty((0,)))
        self.assertEqual(program.items[1].circuit, circuit)
        npt.assert_almost_equal(program.items[1].circuit_arguments, np.array([10]))


class TestQuantumProgramResult(IBMTestCase):
    """Test the QuantumProgramResult class."""

    def test_construct_empty(self):
        """Test simple construction when empty."""
        result = QuantumProgramResult([])
        self.assertFalse(result)
        self.assertEqual(result.metadata, {})

    def test_construct_nonempty(self):
        """Test simple construction when nonempty."""
        result = QuantumProgramResult(
            [
                {"a": np.linspace(0, 1, 20)},
                {"b": np.linspace(0, 1, 5), "c": np.linspace(0, 1, 6)},
            ]
        )
        self.assertEqual(result.metadata, {})
        self.assertEqual(len(result), 2)
        self.assertEqual(list(map(set, result)), [{"a"}, {"b", "c"}])

        self.assertEqual(set(result[0]), {"a"})
        npt.assert_almost_equal(result[0]["a"], np.linspace(0, 1, 20))

        self.assertEqual(set(result[1]), {"b", "c"})
        npt.assert_almost_equal(result[1]["b"], np.linspace(0, 1, 5))
        npt.assert_almost_equal(result[1]["c"], np.linspace(0, 1, 6))
