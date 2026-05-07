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
from qiskit.primitives.containers.estimator_pub import ObservablesArray

from qiskit_ibm_runtime.executor_estimator.utils import (
    get_pauli_basis,
    pauli_to_ints,
    get_bases,
)


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


class TestGetBases(unittest.TestCase):
    """Tests for get_bases function."""

    def test_single_observable_single_term(self):
        """Test with single observable with single term."""
        observables = ObservablesArray.coerce([{"ZZZ": 1}])
        result = get_bases(observables)
        # Should return a single basis that can measure ZZZ
        self.assertEqual(len(result), 1)
        # The basis should be exactly ZZZ (all Z components)
        self.assertEqual(result[0], Pauli("ZZZ"))

    def test_single_observable_x_term(self):
        """Test with single X observable."""
        observables = ObservablesArray.coerce([{"XXX": 1}])
        result = get_bases(observables)
        self.assertEqual(len(result), 1)
        # The basis should be exactly XXX (all X components)
        self.assertEqual(result[0], Pauli("XXX"))

    def test_single_observable_y_term(self):
        """Test with single Y observable."""
        observables = ObservablesArray.coerce([{"YYY": 1}])
        result = get_bases(observables)
        self.assertEqual(len(result), 1)
        # The basis should be exactly YYY (both Z and X components)
        self.assertEqual(result[0], Pauli("YYY"))

    def test_single_observable_mixed_term(self):
        """Test with single mixed Pauli observable."""
        observables = ObservablesArray.coerce([{"XYZ": 1}])
        result = get_bases(observables)
        self.assertEqual(len(result), 1)
        # The basis should be exactly XYZ
        self.assertEqual(result[0], Pauli("XYZ"))

    def test_non_commuting_observables(self):
        """Test with multiple non-commuting observables."""
        observables = ObservablesArray.coerce([{"ZZZ": 1}, {"XXX": 1}])
        result = get_bases(observables)
        # ZZZ and XXX don't commute qubit-wise, should be in separate groups
        self.assertEqual(len(result), 2)
        # Check that both bases are present
        self.assertIn(Pauli("ZZZ"), result)
        self.assertIn(Pauli("XXX"), result)

    def test_commuting_terms_same_positions(self):
        """Test that commuting terms with same Pauli positions are grouped."""
        observables = ObservablesArray.coerce([{"ZZI": 1, "ZIZ": 1, "IZZ": 1}])
        result = get_bases(observables)
        # All terms commute qubit-wise (no conflicts), should be in one group
        self.assertEqual(len(result), 1)
        # The basis should be the OR of all terms: ZZZ
        self.assertEqual(result[0], Pauli("ZZZ"))

    def test_commuting_terms_different_paulis(self):
        """Test commuting terms with different Pauli types."""
        observables = ObservablesArray.coerce([{"XII": 1, "IXI": 1, "IIX": 1}])
        result = get_bases(observables)
        # All X terms on different qubits commute
        self.assertEqual(len(result), 1)
        # The basis should be XXX (OR of all X positions)
        self.assertEqual(result[0], Pauli("XXX"))

    def test_non_commuting_on_same_qubit(self):
        """Test non-commuting terms on the same qubit."""
        observables = ObservablesArray.coerce([{"ZII": 1, "XII": 1}])
        result = get_bases(observables)
        # Z and X on same qubit don't commute, need separate bases
        self.assertEqual(len(result), 2)
        self.assertIn(Pauli("ZII"), result)
        self.assertIn(Pauli("XII"), result)

    def test_partially_commuting_terms(self):
        """Test mix of commuting and non-commuting terms."""
        observables = ObservablesArray.coerce([{"ZZI": 1, "ZIZ": 1, "XXI": 1}])
        result = get_bases(observables)
        # ZZI and ZIZ commute (both Z on first qubit)
        # XXI doesn't commute with them (X vs Z on first qubit)
        self.assertEqual(len(result), 2)
        # First group: ZZI and ZIZ -> ZZZ
        # Second group: XXI -> XXI
        self.assertIn(Pauli("ZZZ"), result)
        self.assertIn(Pauli("XXI"), result)

    def test_identity_terms(self):
        """Test that identity terms are handled correctly."""
        observables = ObservablesArray.coerce([{"III": 1, "ZII": 1}])
        result = get_bases(observables)
        # Identity commutes with everything
        self.assertEqual(len(result), 1)
        # The basis should be ZII (identity doesn't add to basis)
        self.assertEqual(result[0], Pauli("ZII"))

    def test_multiple_observables_array(self):
        """Test with multiple observables in array."""
        observables = ObservablesArray.coerce([{"ZZZ": 1}, {"XXX": 1}, {"YYY": 1}])
        result = get_bases(observables)
        # All three don't commute qubit-wise
        self.assertEqual(len(result), 3)
        self.assertIn(Pauli("ZZZ"), result)
        self.assertIn(Pauli("XXX"), result)
        self.assertIn(Pauli("YYY"), result)

    def test_complex_observable_with_multiple_terms(self):
        """Test observable with multiple terms that partially commute."""
        observables = ObservablesArray.coerce([{"ZZI": 0.5, "IZZ": 0.5, "XXI": 0.3, "IXX": 0.3}])
        result = get_bases(observables)
        # ZZI and IZZ commute -> group 1: ZZZ
        # XXI and IXX commute -> group 2: XXX
        # But ZZZ and XXX don't commute
        self.assertEqual(len(result), 2)
        self.assertIn(Pauli("ZZZ"), result)
        self.assertIn(Pauli("XXX"), result)

    def test_projector_bases(self):
        """Test with projector observables (0, 1, +, -, r, l)."""
        observables = ObservablesArray.coerce([{"000": 1}])
        result = get_bases(observables)
        self.assertEqual(len(result), 1)
        # Projectors 0 and 1 map to Z basis
        self.assertEqual(result[0], Pauli("ZZZ"))

    def test_mixed_projector_and_pauli(self):
        """Test mix of projectors and Pauli operators."""
        observables = ObservablesArray.coerce([{"0ZI": 1, "1ZI": 1}])
        result = get_bases(observables)
        # Both map to Z basis and commute
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], Pauli("ZZI"))

    def test_y_with_z_non_commuting(self):
        """Test Y and Z on same qubit don't commute."""
        observables = ObservablesArray.coerce([{"YII": 1, "ZII": 1}])
        result = get_bases(observables)
        self.assertEqual(len(result), 2)
        self.assertIn(Pauli("YII"), result)
        self.assertIn(Pauli("ZII"), result)

    def test_y_with_x_non_commuting(self):
        """Test Y and X on same qubit don't commute."""
        observables = ObservablesArray.coerce([{"YII": 1, "XII": 1}])
        result = get_bases(observables)
        self.assertEqual(len(result), 2)
        self.assertIn(Pauli("YII"), result)
        self.assertIn(Pauli("XII"), result)

    def test_all_identity_observable(self):
        """Test with all-identity observable."""
        observables = ObservablesArray.coerce([{"III": 1.0}])
        with self.assertRaises(ValueError) as context:
            get_bases(observables)
        self.assertIn("Only identity", str(context.exception))
