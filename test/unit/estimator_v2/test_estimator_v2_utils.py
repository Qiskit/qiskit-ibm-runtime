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

    def test_single_basis_match(self):
        """Test finding a matching basis."""
        pauli = Pauli("ZZZ")
        bases = [Pauli("ZZZ")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        # Verify the basis exactly matches the observable support
        self.assertEqual(bases[result], pauli)

    def test_multiple_bases_first_match(self):
        """Test returns first matching basis."""
        pauli = Pauli("ZZZ")
        bases = [Pauli("ZZZ"), Pauli("ZZZ")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        # Should return the first exactly compatible basis
        self.assertEqual(bases[result], pauli)

    def test_compatible_basis_identity_positions(self):
        """Test finding compatible basis with identity positions."""
        pauli = Pauli("ZZI")
        bases = [Pauli("ZZZ")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        # ZZI can be measured by ZZZ because the non-identity positions match
        self.assertEqual(bases[result].to_label()[:2], "ZZ")

    def test_compatible_basis_subset(self):
        """Test Pauli that is a subset of the basis."""
        pauli = Pauli("ZII")
        bases = [Pauli("ZZZ")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        # ZII can be measured by ZZZ because the non-identity positions match
        self.assertEqual(bases[result].to_label()[0], "Z")

    def test_no_matching_basis_x_vs_z(self):
        """Test raises error when X and Z conflict."""
        pauli = Pauli("XXX")
        bases = [Pauli("ZZZ")]
        with self.assertRaises(ValueError) as context:
            identify_measure_basis(pauli, bases)
        self.assertIn("Cannot compute eval", str(context.exception))

    def test_no_matching_basis_y_vs_z(self):
        """Test raises error when Y and Z conflict."""
        pauli = Pauli("YII")
        bases = [Pauli("ZII")]
        with self.assertRaises(ValueError):
            identify_measure_basis(pauli, bases)

    def test_no_matching_basis_y_vs_x(self):
        """Test raises error when Y and X conflict."""
        pauli = Pauli("YII")
        bases = [Pauli("XII")]
        with self.assertRaises(ValueError):
            identify_measure_basis(pauli, bases)

    def test_multiple_bases_second_match(self):
        """Test returns correct index when first basis doesn't match."""
        pauli = Pauli("XXX")
        bases = [Pauli("ZZZ"), Pauli("XXX")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 1)
        # Should find the second basis, which exactly matches the observable support
        self.assertEqual(bases[result], pauli)

    def test_multiple_bases_third_match(self):
        """Test returns correct index from multiple bases."""
        pauli = Pauli("YYY")
        bases = [Pauli("ZZZ"), Pauli("XXX"), Pauli("YYY")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 2)
        self.assertEqual(bases[result], pauli)

    def test_compatible_mixed_paulis(self):
        """Test compatible basis with mixed Pauli types."""
        pauli = Pauli("XYZ")
        bases = [Pauli("XYZ")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        self.assertEqual(bases[result], pauli)

    def test_compatible_partial_overlap(self):
        """Test basis with partial overlap on different qubits."""
        pauli = Pauli("XII")
        bases = [Pauli("XXX")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        # XII can be measured by XXX because the first qubit matches in X basis
        self.assertEqual(bases[result].to_label()[0], "X")

    def test_identity_pauli_matches_any_basis(self):
        """Test identity Pauli matches any basis."""
        pauli = Pauli("III")
        bases = [Pauli("ZZZ")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        # Identity can be measured from any basis; first basis is accepted
        self.assertEqual(result, 0)

    def test_pauli_with_identity_in_basis(self):
        """Test Pauli with identity positions in basis."""
        pauli = Pauli("ZII")
        bases = [Pauli("ZII")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        self.assertEqual(bases[result], pauli)

    def test_non_commuting_on_single_qubit(self):
        """Test non-commuting Paulis on single qubit position."""
        pauli = Pauli("ZII")
        bases = [Pauli("XII")]
        with self.assertRaises(ValueError):
            identify_measure_basis(pauli, bases)

    def test_commuting_on_different_qubits(self):
        """Test commuting Paulis on different qubits."""
        pauli = Pauli("ZII")
        bases = [Pauli("IXI")]
        with self.assertRaises(ValueError):
            identify_measure_basis(pauli, bases)

    def test_y_basis_exact_match(self):
        """Test Y basis exact match."""
        pauli = Pauli("YYY")
        bases = [Pauli("YYY")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        self.assertEqual(bases[result], pauli)

    def test_complex_commutation_pattern(self):
        """Test complex commutation pattern with mixed Paulis."""
        pauli = Pauli("XYZI")
        bases = [Pauli("XYZI")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        self.assertEqual(bases[result], pauli)

    def test_basis_superset_of_pauli(self):
        """Test basis that is a superset of the Pauli."""
        pauli = Pauli("ZII")
        bases = [Pauli("ZXY")]
        result = identify_measure_basis(pauli, bases)
        self.assertEqual(result, 0)
        # ZII can be measured by ZXY because qubit 0 matches in Z basis
        self.assertEqual(bases[result].to_label()[0], "Z")

    def test_empty_bases_list(self):
        """Test with empty bases list raises error."""
        pauli = Pauli("ZZZ")
        bases = []
        with self.assertRaises(ValueError):
            identify_measure_basis(pauli, bases)


class TestComputeExpVal(unittest.TestCase):
    """Tests for compute_exp_val function."""

    def test_all_zeros_z_basis(self):
        """Test expectation value for all zeros in Z basis."""
        # ZZZ observable, all measurements are 000
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=3)
        datum = np.array([[[[False, False, False]] * 10]])
        exp_val, variance = compute_exp_val("ZZZ", datum)
        # All eigenvalues are +1, so expectation value is 1.0
        np.testing.assert_almost_equal(exp_val, 1.0)
        # Variance should be 0 (no variance)
        np.testing.assert_almost_equal(variance, 0.0)

    def test_all_ones_z_basis(self):
        """Test expectation value for all ones in Z basis."""
        # ZZZ observable, all measurements are 111
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=3)
        datum = np.array([[[[True, True, True]] * 10]])
        exp_val, variance = compute_exp_val("ZZZ", datum)
        # All eigenvalues are -1, so expectation value is -1.0
        np.testing.assert_almost_equal(exp_val, -1.0)
        # Variance should be 0 (no variance)
        np.testing.assert_almost_equal(variance, 0.0)

    def test_mixed_measurements(self):
        """Test expectation value for mixed measurements."""
        # Z observable on single qubit, 5 zeros and 5 ones
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=1)
        datum = np.array([[[[False]] * 5 + [[True]] * 5]])
        exp_val, variance = compute_exp_val("Z", datum)
        # 5 * (+1) + 5 * (-1) = 0, so expectation value is 0.0
        np.testing.assert_almost_equal(exp_val, 0.0)
        # Variance should be non-zero
        self.assertGreater(variance, 0.0)

    def test_identity_observable(self):
        """Test expectation value for identity observable."""
        # I observable, any measurements
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=1)
        datum = np.array([[[[False]] * 5 + [[True]] * 5]])
        exp_val, variance = compute_exp_val("I", datum)
        # Identity always gives +1
        np.testing.assert_almost_equal(exp_val, 1.0)
        # Variance should be 0 (no variance)
        np.testing.assert_almost_equal(variance, 0.0)

    def test_projector_zero(self):
        """Test expectation value for projector |0><0|."""
        # Projector on |0> state
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=1)
        datum = np.array([[[[False]] * 7 + [[True]] * 3]])
        exp_val, variance = compute_exp_val("0", datum)
        # Only zeros contribute, 7/10 = 0.7
        np.testing.assert_almost_equal(exp_val, 0.7)
        # Variance should be non-zero
        self.assertGreater(variance, 0.0)

    def test_projector_one(self):
        """Test expectation value for projector |1><1|."""
        # Projector on |1> state
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=1)
        datum = np.array([[[[False]] * 3 + [[True]] * 7]])
        exp_val, variance = compute_exp_val("1", datum)
        # Only ones contribute, 7/10 = 0.7
        np.testing.assert_almost_equal(exp_val, 0.7)
        # Variance should be non-zero
        self.assertGreater(variance, 0.0)

    def test_multi_qubit_observable(self):
        """Test expectation value for multi-qubit observable."""
        # ZZ observable, measurements: 00, 01, 10, 11 (equal distribution)

    def test_std_calculation_known_variance(self):
        """Test variance calculation with known variance."""
        # Z observable with 50/50 split between +1 and -1 eigenvalues
        # This gives variance = 1
        # Shape: (num_randomizations=1, shots_per_randomization=100, num_qubits=1)
        datum = np.array([[[[False]] * 50 + [[True]] * 50]])
        exp_val, variance = compute_exp_val("Z", datum)

        # Expectation value should be 0
        np.testing.assert_almost_equal(exp_val, 0.0)

        # For eigenvalues ±1 with equal probability:
        # variance = E[X²] - E[X]² = 1 - 0 = 1
        expected_variance = 1.0
        np.testing.assert_almost_equal(variance, expected_variance, decimal=10)

    def test_std_calculation_projector_variance(self):
        """Test variance calculation for projector with known variance."""
        # Projector |0><0| with 70% zeros, 30% ones
        # Eigenvalues: 1 for zeros, 0 for ones
        # Mean = 0.7, variance = E[X²] - E[X]² = 0.7 - 0.49 = 0.21
        # Shape: (num_randomizations=1, shots_per_randomization=100, num_qubits=1)
        datum = np.array([[[[False]] * 70 + [[True]] * 30]])
        exp_val, variance = compute_exp_val("0", datum)

        np.testing.assert_almost_equal(exp_val, 0.7)

        # variance = E[X²] - E[X]² = 0.7 - 0.49 = 0.21
        expected_variance = 0.7 - 0.49
        np.testing.assert_almost_equal(variance, expected_variance, decimal=10)

    def test_std_multi_qubit_with_variance(self):
        """Test variance calculation for multi-qubit observable with variance."""
        # ZZ observable with specific distribution
        # 00 -> +1, 01 -> -1, 10 -> -1, 11 -> +1
        # 10 shots: 3x(00), 2x(01), 2x(10), 3x(11)
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=2)
        datum = np.array(
            [
                [
                    [[False, False]] * 3  # 00 -> +1
                    + [[False, True]] * 2  # 01 -> -1
                    + [[True, False]] * 2  # 10 -> -1
                    + [[True, True]] * 3  # 11 -> +1
                ]
            ]
        )
        exp_val, variance = compute_exp_val("ZZ", datum)

        # Mean = (3*1 + 2*(-1) + 2*(-1) + 3*1) / 10 = 2/10 = 0.2
        np.testing.assert_almost_equal(exp_val, 0.2)

        # E[X²] = (3*1 + 2*1 + 2*1 + 3*1) / 10 = 10/10 = 1.0
        # variance = 1.0 - 0.04 = 0.96
        expected_variance = 1.0 - 0.04
        np.testing.assert_almost_equal(variance, expected_variance, decimal=10)

    def test_std_with_parameter_sweep(self):
        """Test variance calculation with parameter sweep dimensions."""
        # Test with shape (num_randomizations, param_sweep, shots_per_randomization, num_qubits)
        # 1 randomization, 2 parameter values, 10 shots each, 1 qubit
        datum = np.array(
            [
                [
                    [[False]] * 8 + [[True]] * 2,  # First param: 80% zeros
                    [[False]] * 5 + [[True]] * 5,  # Second param: 50% zeros
                ]
            ]
        )
        exp_vals, variances = compute_exp_val("Z", datum)

        # Check shapes
        self.assertEqual(exp_vals.shape, (2,))
        self.assertEqual(variances.shape, (2,))

        # First parameter: 8 zeros (+1) and 2 ones (-1)
        # mean = (8*1 + 2*(-1))/10 = 0.6
        # E[X²] = (8*1² + 2*(-1)²)/10 = 1.0
        # variance = 1.0 - 0.36 = 0.64
        np.testing.assert_almost_equal(exp_vals[0], 0.6)
        expected_variance_0 = 0.64
        np.testing.assert_almost_equal(variances[0], expected_variance_0, decimal=10)

        # Second parameter: 5 zeros (+1) and 5 ones (-1)
        # mean = 0.0
        # E[X²] = 1.0
        # variance = 1.0 - 0.0 = 1.0
        np.testing.assert_almost_equal(exp_vals[1], 0.0)
        expected_variance_1 = 1.0
        np.testing.assert_almost_equal(variances[1], expected_variance_1, decimal=10)

    def test_std_projector_all_filtered(self):
        """Test variance when projector filters out all measurements."""
        # Projector |0><0| but all measurements are |1>
        # Shape: (num_randomizations=1, shots_per_randomization=10, num_qubits=1)
        datum = np.array([[[[True]] * 10]])
        exp_val, variance = compute_exp_val("0", datum)

        # All measurements filtered out, so exp_val = 0
        np.testing.assert_almost_equal(exp_val, 0.0)
        # variance should also be 0 (no variance when all are filtered)
        np.testing.assert_almost_equal(variance, 0.0)
        # Shape: (num_randomizations=1, shots_per_randomization=4, num_qubits=2)
        datum = np.array(
            [
                [
                    [
                        [False, False],  # 00 -> +1
                        [False, True],  # 01 -> -1
                        [True, False],  # 10 -> -1
                        [True, True],  # 11 -> +1
                    ]
                ]
            ]
        )
        exp_val, variance = compute_exp_val("ZZ", datum)
        # (+1 - 1 - 1 + 1) / 4 = 0
        np.testing.assert_almost_equal(exp_val, 0.0)
        # Variance should be non-zero (has variance)
        self.assertGreater(variance, 0.0)
