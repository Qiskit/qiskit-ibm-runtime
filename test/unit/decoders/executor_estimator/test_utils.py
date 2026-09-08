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

"""Tests for executor estimator decoder utils."""

import numpy as np
from qiskit.quantum_info import Pauli

from qiskit_ibm_runtime.decoders.executor_estimator.utils import get_pauli_basis, project_to_z

from ....ibm_test_case import IBMTestCase


class TestProjectToZ(IBMTestCase):
    """Tests for project_to_z function."""

    def test_single_qubit_projections(self):
        """Test single-qubit projection to Z basis."""
        for observable, expected in [
            ("Z", np.array(["Z"])),
            ("X", np.array(["Z"])),
            ("Y", np.array(["Z"])),
            ("0", np.array(["0"])),
            ("1", np.array(["1"])),
            ("I", np.array(["I"])),
        ]:
            with self.subTest(observable=observable):
                result = project_to_z(observable)
                np.testing.assert_array_equal(result, expected)

    def test_multi_qubit_projection(self):
        """Test multi-qubit projection."""
        result = project_to_z("ZX0I")
        np.testing.assert_array_equal(result, np.array(["Z", "Z", "0", "I"]))


class TestGetPauliBasis(IBMTestCase):
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
