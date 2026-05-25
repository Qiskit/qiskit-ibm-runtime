# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Unit tests for EstimatorV2 helper functions."""

import unittest

from qiskit.quantum_info import Pauli

from qiskit_ibm_runtime.executor_estimator.utils import get_pauli_basis, pauli_to_ints


class TestGetPauliBasis(unittest.TestCase):
    """Tests for get_pauli_basis function."""

    def test_single_qubit_bases(self):
        """Test single-qubit basis conversions."""
        for basis, expected in [
            ("0", Pauli("Z")),
            ("1", Pauli("Z")),
            ("+", Pauli("X")),
            ("-", Pauli("X")),
            ("r", Pauli("Y")),
            ("l", Pauli("Y")),
            ("I", Pauli("I")),
        ]:
            with self.subTest(basis=basis):
                result = get_pauli_basis(basis)
                self.assertEqual(result, expected)

    def test_multi_qubit(self):
        """Test multi-qubit basis conversion."""
        result = get_pauli_basis("0+r")
        expected = Pauli("ZXY")
        self.assertEqual(result, expected)


class TestPauliToInts(unittest.TestCase):
    """Tests for pauli_to_ints function."""

    def test_single_qubit_paulis(self):
        """Test single-qubit Pauli to integer conversions."""
        for pauli, expected in [
            (Pauli("I"), [0]),
            (Pauli("Z"), [1]),
            (Pauli("X"), [2]),
            (Pauli("Y"), [3]),
        ]:
            with self.subTest(pauli=str(pauli)):
                result = pauli_to_ints(pauli)
                self.assertEqual(result, expected)

    def test_multi_qubit(self):
        """Test multi-qubit Pauli conversion."""
        result = pauli_to_ints(Pauli("IZXY"))
        self.assertEqual(result, [3, 2, 1, 0])
