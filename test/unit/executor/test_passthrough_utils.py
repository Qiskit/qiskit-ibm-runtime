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

"""Tests for passthrough_utils module."""

import unittest

from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor.passthrough_utils import validate_and_extract_metadata


@ddt
class TestValidateAndExtractMetadata(unittest.TestCase):
    """Tests for validate_and_extract_metadata function."""

    def test_valid_metadata_sampler_pub(self):
        """Test that valid metadata passes validation for sampler pubs."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)
        circuit1.measure_all()
        circuit1.metadata = {"experiment_id": "test_123", "custom_field": [1, 2, 3]}

        circuit2 = QuantumCircuit(2)
        circuit2.h(1)
        circuit2.measure_all()
        # No metadata set (empty dict)

        pub1 = SamplerPub.coerce(circuit1)
        pub2 = SamplerPub.coerce(circuit2)
        metadata_list = validate_and_extract_metadata([pub1, pub2])

        self.assertEqual(len(metadata_list), 2)
        self.assertEqual(metadata_list[0], circuit1.metadata)
        self.assertEqual(metadata_list[1], {})

    def test_valid_metadata_estimator_pub(self):
        """Test that valid metadata passes validation for estimator pubs."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)
        circuit1.metadata = {"experiment_id": "test_456", "nested": {"key": "value"}}

        circuit2 = QuantumCircuit(2)
        circuit2.h(1)
        # No metadata set (empty dict)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub1 = EstimatorPub.coerce((circuit1, observable))
        pub2 = EstimatorPub.coerce((circuit2, observable))
        metadata_list = validate_and_extract_metadata([pub1, pub2])

        self.assertEqual(len(metadata_list), 2)
        self.assertEqual(metadata_list[0], circuit1.metadata)
        self.assertEqual(metadata_list[1], {})

    @data(
        {"invalid": range(3)},  # generators is not DataTree compatible
        {"invalid": {1, 2, 3}},  # set is not DataTree compatible
        {"invalid": object()},  # custom object is not DataTree compatible
    )
    def test_invalid_metadata_raises_error(self, invalid_metadata):
        """Test that circuit with invalid metadata raises an error."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        circuit.metadata = invalid_metadata

        pub = SamplerPub.coerce(circuit)

        with self.assertRaises(IBMInputValueError) as context:
            validate_and_extract_metadata([pub])

        self.assertIn("metadata", str(context.exception).lower())
        self.assertIn("DataTree", str(context.exception))
        self.assertIn("index 0", str(context.exception))

    def test_invalid_metadata_in_second_pub_raises_error(self):
        """Test that invalid metadata in second pub raises error with correct index."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.metadata = {"valid": "metadata"}

        circuit2 = QuantumCircuit(2)
        circuit2.h(1)
        circuit2.metadata = {"invalid": range(3)}  # Invalid tuple

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pubs = [
            EstimatorPub.coerce((circuit1, observable)),
            EstimatorPub.coerce((circuit2, observable)),
        ]

        with self.assertRaises(IBMInputValueError) as context:
            validate_and_extract_metadata(pubs)

        self.assertIn("index 1", str(context.exception))
        self.assertIn("DataTree", str(context.exception))
