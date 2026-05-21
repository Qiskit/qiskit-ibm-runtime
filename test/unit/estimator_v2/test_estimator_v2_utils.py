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
import numpy as np
from qiskit.quantum_info import Pauli
from qiskit.primitives.containers.estimator_pub import ObservablesArray


from qiskit_ibm_runtime.executor_estimator.utils import (
    get_pauli_basis,
    pauli_to_ints,
    get_bases,
    project_to_z,
    identify_measure_basis,
    compute_exp_val,
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

    def test_commuting_terms(self):
        """Test that commuting terms with same Pauli positions are grouped."""
        observables = ObservablesArray.coerce([{"ZZI": 1, "ZIZ": 1, "IZZ": 1}])
        result = get_bases(observables)
        # All terms commute qubit-wise (no conflicts), should be in one group
        self.assertEqual(len(result), 1)
        # The basis should be the OR of all terms: ZZZ
        self.assertEqual(result[0], Pauli("ZZZ"))

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

    def test_all_identity_observable_raises(self):
        """Test that error is raised with all-identity observable."""
        observables = ObservablesArray.coerce([{"III": 1.0}])
        with self.assertRaises(ValueError) as context:
            get_bases(observables)
        self.assertIn("Only identity", str(context.exception))


class TestProjectToZ(unittest.TestCase):
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


class TestIdentifyMeasureBasis(unittest.TestCase):
    """Tests for identify_measure_basis function."""

    def test_identify_measure_basis(self):
        """Test identify_measure_basis with various observable and basis combinations."""
        test_cases = [
            # (observable, bases_with_indices, expected_config_idx, description)
            ("ZZZ", [(Pauli("ZZZ"), 0)], 0, "single basis match"),
            ("ZZZ", [(Pauli("ZZZ"), 0), (Pauli("ZXZ"), 1)], 0, "multiple bases first match"),
            ("ZZI", [(Pauli("ZZZ"), 0)], 0, "compatible basis with identity positions"),
            ("XXX", [(Pauli("ZZZ"), 0), (Pauli("XXX"), 1)], 1, "multiple bases second match"),
            ("XYZ", [(Pauli("XYZ"), 5)], 5, "compatible mixed paulis"),
            ("III", [(Pauli("ZZZ"), 10)], 10, "identity"),
        ]

        for observable, bases_with_indices, expected_config_idx, description in test_cases:
            with self.subTest(description=description, observable=observable):
                pauli = Pauli(observable)
                result = identify_measure_basis(pauli, bases_with_indices)
                self.assertEqual(result, expected_config_idx)

    def test_identify_measure_basis_errors(self):
        """Test identify_measure_basis raises errors for incompatible observables."""
        error_cases = [
            # (observable, bases_with_indices, description)
            ("XXX", [(Pauli("ZZZ"), 0)], "X vs Z conflict"),
            ("YII", [(Pauli("ZII"), 0)], "Y vs Z conflict"),
            ("YII", [(Pauli("XII"), 0)], "Y vs X conflict"),
            ("ZZZ", [], "empty bases list"),
        ]

        for observable, bases_with_indices, description in error_cases:
            with self.subTest(description=description, observable=observable):
                pauli = Pauli(observable)
                with self.assertRaises(ValueError, msg=f"Failed to raise error for {description}"):
                    identify_measure_basis(pauli, bases_with_indices)


class TestComputeExpVal(unittest.TestCase):
    """Tests for compute_exp_val function."""

    def test_observable_combinations(self):
        """Test compute_exp_val with various observable character combinations.

        Note: Observable strings are read RIGHT-TO-LEFT for qubit indexing.
        E.g., "I0" means qubit 0 has projector "0", qubit 1 has identity "I".
        Measurement arrays are [qubit0, qubit1, ...].
        """
        test_cases = [
            # (observable, measurements, expected_exp_val, expected_variance, description)
            # Single qubit observables (using 80/20 split to show non-trivial behavior)
            ("X", [[False]] * 8 + [[True]] * 2, 0.6, 0.64, "X"),
            ("Y", [[False]] * 8 + [[True]] * 2, 0.6, 0.64, "Y"),
            ("Z", [[False]] * 8 + [[True]] * 2, 0.6, 0.64, "Z"),
            ("I", [[False]] * 8 + [[True]] * 2, 1.0, 0.0, "I"),
            # Two-qubit: Identity + projectors
            ("I+", [[False, False]] * 7 + [[True, False]] * 3, 0.7, 0.21, "I+"),
            ("I-", [[False, False]] * 3 + [[True, False]] * 7, 0.7, 0.21, "I-"),
            ("Ir", [[False, False]] * 7 + [[True, False]] * 3, 0.7, 0.21, "Ir"),
            ("Il", [[False, False]] * 3 + [[True, False]] * 7, 0.7, 0.21, "Il"),
            ("I0", [[False, False]] * 7 + [[True, False]] * 3, 0.7, 0.21, "I0"),
            ("I1", [[False, False]] * 3 + [[True, False]] * 7, 0.7, 0.21, "I1"),
            ("XY+", [[False, False, False]] * 5 + [[False, True, True]] * 5, 1.0, 0.0, "XY+"),
        ]

        for observable, measurements, exp_val, variance, desc in test_cases:
            with self.subTest(desc=desc):
                # Shape: (num_randomizations=1, shots_per_randomization=N, num_qubits)
                datum = np.array([[measurements]])
                result_exp_val, result_variance = compute_exp_val(observable, datum)

                np.testing.assert_almost_equal(
                    result_exp_val,
                    exp_val,
                    decimal=10,
                )
                np.testing.assert_almost_equal(
                    result_variance,
                    variance,
                    decimal=10,
                )

    def test_multiple_randomizations(self):
        """Test variance calculation with multiple randomizations.

        With multiple randomizations, the variance should be computed across
        all randomizations and shots combined.
        """
        # Shape: (num_randomizations=3, shots_per_randomization=10, num_qubits=1)
        # Create 3 randomizations with different distributions
        datum = np.array(
            [
                [[[False]] * 8 + [[True]] * 2],  # Randomization 1: 80% zeros
                [[[False]] * 5 + [[True]] * 5],  # Randomization 2: 50% zeros
                [[[False]] * 7 + [[True]] * 3],  # Randomization 3: 70% zeros
            ]
        )
        exp_val, variance = compute_exp_val("Z", datum)

        # Total shots = 3 randomizations × 10 shots = 30 shots
        expected_exp_val = 10 / 30
        np.testing.assert_almost_equal(exp_val, expected_exp_val, decimal=10)

        expected_variance = 1.0 - (10 / 30) ** 2
        np.testing.assert_almost_equal(variance, expected_variance, decimal=10)
