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
from unittest.mock import Mock, patch
import numpy as np


from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2
from qiskit_ibm_runtime.quantum_program.quantum_program_result import (
    QuantumProgramResult,
    Metadata,
)
from qiskit_ibm_runtime.quantum_program.post_processors import POST_PROCESSORS


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

    def _create_job(self, post_processor=None):
        """Helper to create a RuntimeJobV2 instance."""
        return RuntimeJobV2(
            backend=self.mock_backend,
            api_client=self.mock_api_client,
            job_id="test_job_id",
            program_id="executor",
            service=self.mock_service,
            post_processor=post_processor,
        )

    def test_apply_post_processing_non_qp_result(self):
        """Test that non-QuantumProgramResult is returned unchanged."""
        job = self._create_job()

        # Test with various non-QuantumProgramResult types
        for result in ["string_result", 123, {"dict": "result"}, None]:
            processed = job._apply_post_processing(result, None)
            self.assertEqual(processed, result)

    def test_apply_post_processing_no_processor(self):
        """Test that QuantumProgramResult without processor is returned unchanged."""
        job = self._create_job()
        qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

        processed = job._apply_post_processing(qp_result, None)
        self.assertEqual(processed, qp_result)

    def test_apply_post_processing_with_override(self):
        """Test post-processing with override parameter."""

        # Register a test post-processor
        def test_processor(qp_result, metadata):
            return "override_result"

        POST_PROCESSORS["test_override"] = test_processor

        try:
            job = self._create_job()
            qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

            # Apply with override
            processed = job._apply_post_processing(qp_result, "test_override")
            self.assertEqual(processed, "override_result")
        finally:
            # Clean up
            del POST_PROCESSORS["test_override"]

    def test_apply_post_processing_with_job_processor(self):
        """Test post-processing with job's stored processor."""

        # Register a test post-processor
        def test_processor(qp_result, metadata):
            return "job_processor_result"

        POST_PROCESSORS["test_job_processor"] = test_processor

        try:
            job = self._create_job(post_processor="test_job_processor")
            qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

            # Apply with job's processor
            processed = job._apply_post_processing(qp_result, None)
            self.assertEqual(processed, "job_processor_result")
        finally:
            # Clean up
            del POST_PROCESSORS["test_job_processor"]

    def test_apply_post_processing_with_passthrough_data(self):
        """Test post-processing with passthrough_data."""

        # Register a test post-processor
        def test_processor(qp_result, metadata):
            return f"passthrough_result_{metadata.get('test_key')}"

        POST_PROCESSORS["test_passthrough"] = test_processor

        try:
            job = self._create_job()
            qp_result = QuantumProgramResult(
                data=[{"c": np.array([[0, 1]])}],
                metadata=Metadata(),
                passthrough_data={
                    "post_processor": {
                        "name": "test_passthrough",
                        "metadata": {"test_key": "test_value"},
                    }
                },
            )

            # Apply with passthrough_data
            processed = job._apply_post_processing(qp_result, None)
            self.assertEqual(processed, "passthrough_result_test_value")
        finally:
            # Clean up
            del POST_PROCESSORS["test_passthrough"]

    def test_post_processing_precedence(self):
        """Test that override > job processor > passthrough_data."""
        # Register test post-processors
        POST_PROCESSORS["override_proc"] = lambda qp, m: "override"
        POST_PROCESSORS["job_proc"] = lambda qp, m: "job"
        POST_PROCESSORS["passthrough_proc"] = lambda qp, m: "passthrough"

        try:
            # Test 1: Override takes precedence over job processor
            job = self._create_job(post_processor="job_proc")
            qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

            processed = job._apply_post_processing(qp_result, "override_proc")
            self.assertEqual(processed, "override")

            # Test 2: Job processor takes precedence over passthrough_data
            qp_result_with_passthrough = QuantumProgramResult(
                data=[{"c": np.array([[0, 1]])}],
                metadata=Metadata(),
                passthrough_data={"post_processor": {"name": "passthrough_proc", "metadata": {}}},
            )

            processed = job._apply_post_processing(qp_result_with_passthrough, None)
            self.assertEqual(processed, "job")

            # Test 3: Passthrough_data used when no override or job processor
            job_no_processor = self._create_job()
            processed = job_no_processor._apply_post_processing(qp_result_with_passthrough, None)
            self.assertEqual(processed, "passthrough")
        finally:
            # Clean up
            del POST_PROCESSORS["override_proc"]
            del POST_PROCESSORS["job_proc"]
            del POST_PROCESSORS["passthrough_proc"]

    def test_post_processing_unknown_processor_name(self):
        """Test warning when processor name is not in registry."""
        job = self._create_job(post_processor="unknown_processor")
        qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

        # Should return unchanged result and log warning
        processed = job._apply_post_processing(qp_result, None)
        self.assertEqual(processed, qp_result)

    def test_post_processing_error_propagation(self):
        """Test that post-processing errors are propagated."""

        def failing_processor(qp_result, metadata):
            raise RuntimeError("Test error")

        POST_PROCESSORS["failing_proc"] = failing_processor

        try:
            job = self._create_job()
            qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

            with self.assertRaises(RuntimeError) as context:
                job._apply_post_processing(qp_result, "failing_proc")

            self.assertIn("Test error", str(context.exception))
        finally:
            # Clean up
            del POST_PROCESSORS["failing_proc"]

    def test_result_with_post_processor_parameter(self):
        """Test result() with post_processor parameter."""
        # Register a test post-processor
        POST_PROCESSORS["test_param_proc"] = lambda qp, m: "param_result"

        try:
            job = self._create_job()
            job._status = "DONE"

            # Mock the API response
            self.mock_api_client.job_results.return_value = '{"test": "data"}'

            # Mock decoder to return QuantumProgramResult
            mock_decoder = Mock()
            mock_decoder.decode.return_value = self.qp_result
            job._final_result_decoder = mock_decoder  # type: ignore[assignment]

            # Call result with post_processor parameter
            result = job.result(post_processor="test_param_proc")

            self.assertEqual(result, "param_result")
        finally:
            # Clean up
            del POST_PROCESSORS["test_param_proc"]
