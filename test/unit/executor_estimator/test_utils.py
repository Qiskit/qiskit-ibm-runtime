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

"""Unit tests for Estimator helper functions."""

from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.utils import resolve_precision

from ...ibm_test_case import IBMTestCase


class TestResolvePrecision(IBMTestCase):
    """Tests for resolve_precision function."""

    def setUp(self):
        """Set up test fixtures."""
        self.circuit = QuantumCircuit(2)
        self.circuit.h(0)
        self.observable = SparsePauliOp.from_list([("ZZ", 1)])

    def test_all_pubs_with_same_precision(self):
        """Test when all pubs have the same precision value."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        pub3 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)

        result = resolve_precision([pub1, pub2, pub3])
        self.assertEqual(result, 0.01)

    def test_all_pubs_without_precision_with_run_precision(self):
        """Test when no pubs have precision but run_precision is provided."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable))
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))
        pub3 = EstimatorPub.coerce((self.circuit, self.observable))

        result = resolve_precision([pub1, pub2, pub3], run_precision=0.02)
        self.assertEqual(result, 0.02)

    def test_all_pubs_without_precision_no_run_precision(self):
        """Test when no pubs have precision and no run_precision is provided."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable))
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))

        result = resolve_precision([pub1, pub2])
        self.assertIsNone(result)

    def test_mixture_some_with_precision_some_without_matching_run_precision(self):
        """Test mixture where all pubs resolve to same value."""
        # Pubs with explicit precision
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        # Pubs without precision (will use run_precision)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))
        pub3 = EstimatorPub.coerce((self.circuit, self.observable))

        # run_precision matches the explicit precision
        result = resolve_precision([pub1, pub2, pub3], run_precision=0.01)
        self.assertEqual(result, 0.01)

    def test_mixture_some_with_precision_some_without_mismatched_run_precision(self):
        """Test mixture where pubs have different precision values (explicit vs run_precision)."""
        # Pub with explicit precision
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        # Pubs without precision (will use run_precision which is different)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))
        pub3 = EstimatorPub.coerce((self.circuit, self.observable))

        # run_precision is different from explicit precision
        with self.assertRaises(IBMInputValueError) as context:
            resolve_precision([pub1, pub2, pub3], run_precision=0.02)

        self.assertIn("same precision", str(context.exception))

    def test_mixture_multiple_different_explicit_precisions(self):
        """Test mixture where pubs have different explicit precision values."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.02)
        pub3 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.03)

        with self.assertRaises(IBMInputValueError) as context:
            resolve_precision([pub1, pub2, pub3])

        self.assertIn("same precision", str(context.exception))

    def test_pub_level_zero_precision_raises(self):
        """Test that a pub-level precision of 0 is rejected."""
        pub = EstimatorPub.coerce((self.circuit, self.observable), precision=0)

        with self.assertRaisesRegex(IBMInputValueError, "must be strictly greater than 0"):
            resolve_precision([pub])

    def test_run_level_zero_precision_raises(self):
        """Test that a run-level precision of 0 is rejected when pubs have no precision."""
        pub = EstimatorPub.coerce((self.circuit, self.observable))

        with self.assertRaisesRegex(IBMInputValueError, "must be strictly greater than 0"):
            resolve_precision([pub], run_precision=0)
