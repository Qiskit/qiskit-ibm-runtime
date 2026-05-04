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

"""Unit tests for RuntimeJobV2 post-processing."""

import unittest
from unittest.mock import Mock
import numpy as np


from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2
from qiskit_ibm_runtime.quantum_program.quantum_program_result import (
    QuantumProgramResult,
    Metadata,
)
from qiskit_ibm_runtime.sampler_v2 import SAMPLER_POST_PROCESSORS


class TestRuntimeJobPostProcessing(unittest.TestCase):
    """Test RuntimeJobV2 post-processing logic."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock objects
        self.mock_backend = Mock()
        self.mock_backend.name = "test_backend"
        self.mock_api_client = Mock()
        self.mock_service = Mock()

        # Create a simple QuantumProgramResult for testing
        self.qp_result = QuantumProgramResult(
            data=[{"c": np.array([[0, 1], [1, 0]], dtype=np.uint8)}],
            metadata=Metadata(),
        )

        # Store original processors to restore later
        self.original_processors = SAMPLER_POST_PROCESSORS.copy()

        # Register generic test post-processors (reusable with any version)
        SAMPLER_POST_PROCESSORS["v0.1"] = self._simple_processor
        SAMPLER_POST_PROCESSORS["failing_version"] = self._failing_processor

    @staticmethod
    def _simple_processor(qp_result):
        """Simple test processor that returns a fixed string."""
        return "processed_result"

    @staticmethod
    def _failing_processor(qp_result):
        """Test processor that raises an error."""
        raise RuntimeError("Test error")

    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original processors
        SAMPLER_POST_PROCESSORS.clear()
        SAMPLER_POST_PROCESSORS.update(self.original_processors)

    def _create_job(self):
        """Helper to create a RuntimeJobV2 instance."""
        return RuntimeJobV2(
            backend=self.mock_backend,
            api_client=self.mock_api_client,
            job_id="test_job_id",
            program_id="executor",
            service=self.mock_service,
        )

    def test_apply_post_processing_non_qp_result(self):
        """Test that non-QuantumProgramResult is returned unchanged."""
        job = self._create_job()

        # Test with various non-QuantumProgramResult types
        for result in ["string_result", 123, {"dict": "result"}, None]:
            processed = job._apply_post_processing(result)
            self.assertEqual(processed, result)

    def test_apply_post_processing_no_processor(self):
        """Test that QuantumProgramResult with unset semantic role is returned unchanged."""
        job = self._create_job()
        qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

        processed = job._apply_post_processing(qp_result)
        self.assertEqual(processed, qp_result)

    def test_apply_post_processing_with_semantic_role(self):
        """Test post-processing for QuantumProgramResult with set semantic role."""
        job = self._create_job()
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[0, 1]])}],
            metadata=Metadata(),
            passthrough_data={"post_processor": {"version": "v0.1"}},
        )
        qp_result._semantic_role = "sampler_v2"

        # Apply with passthrough_data (uses pre-registered "v0.1" processor)
        processed = job._apply_post_processing(qp_result)
        self.assertEqual(processed, "processed_result")

    def test_passthrough_data_unsupported_semantic_role(self):
        """Test that results with unsupported semantic role raise an error."""
        job = self._create_job()
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[0, 1]])}],
            metadata=Metadata(),
            passthrough_data={"post_processor": {"version": "v0.1"}},
        )
        qp_result._semantic_role = "unsupported_semantic_role"

        # Should raise an error since semantic role is not supported
        with self.assertRaises(ValueError) as context:
            job._apply_post_processing(qp_result)

        self.assertIn("No post-processor found for result with", str(context.exception))

    def test_passthrough_data_missing_version(self):
        """Test that passthrough_data without version raises ValueError for sampler_v2."""
        job = self._create_job()
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[0, 1]])}],
            metadata=Metadata(),
            passthrough_data={
                "post_processor": {}  # Missing "version" field
            },
        )
        qp_result._semantic_role = "sampler_v2"

        # Should raise ValueError since version is required for sampler_v2 context
        with self.assertRaises(ValueError) as context:
            job._apply_post_processing(qp_result)

        self.assertIn("Could not determine a post-processor version", str(context.exception))
