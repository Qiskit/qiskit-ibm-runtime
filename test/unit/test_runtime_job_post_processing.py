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
from qiskit_ibm_runtime.executor.routines.sampler_v2.sampler_post_processors import (
    SAMPLER_POST_PROCESSORS,
)


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
        SAMPLER_POST_PROCESSORS["v1"] = self._simple_processor
        SAMPLER_POST_PROCESSORS["failing_version"] = self._failing_processor

    @staticmethod
    def _simple_processor(qp_result): # pylint: disable=unused-argument
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
        job = self._create_job()
        qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

        # Define override processor inline for this specific test
        def override_proc(qp_result): # pylint: disable=unused-argument
            return "override_result"

        processed = job._apply_post_processing(qp_result, override_proc)
        self.assertEqual(processed, "override_result")

    def test_apply_post_processing_with_passthrough_data(self):
        """Test post-processing with passthrough_data."""
        job = self._create_job()
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[0, 1]])}],
            metadata=Metadata(),
            passthrough_data={
                "post_processor": {
                    "context": "sampler_v2",
                    "version": "v1",
                }
            },
        )

        # Apply with passthrough_data (uses pre-registered "v1" processor)
        processed = job._apply_post_processing(qp_result, None)
        self.assertEqual(processed, "processed_result")

    def test_post_processing_precedence(self):
        """Test that override > passthrough_data."""
        job = self._create_job()

        # Create result with passthrough_data
        qp_result_with_passthrough = QuantumProgramResult(
            data=[{"c": np.array([[0, 1]])}],
            metadata=Metadata(),
            passthrough_data={
                "post_processor": {
                    "context": "sampler_v2",
                    "version": "v1",
                }
            },
        )

        # Test 1: Override takes precedence over passthrough_data
        def override_proc(qp_result): # pylint: disable=unused-argument
            return "override"

        processed = job._apply_post_processing(qp_result_with_passthrough, override_proc)
        self.assertEqual(processed, "override")

        # Test 2: Passthrough_data used when no override
        processed = job._apply_post_processing(qp_result_with_passthrough, None)
        self.assertEqual(processed, "processed_result")

    def test_passthrough_data_wrong_context(self):
        """Test that passthrough_data with wrong context is ignored."""
        job = self._create_job()
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[0, 1]])}],
            metadata=Metadata(),
            passthrough_data={
                "post_processor": {
                    "context": "wrong_context",
                    "version": "v1",
                }
            },
        )

        # Should return unchanged since context is not registered
        processed = job._apply_post_processing(qp_result, None)
        self.assertEqual(processed, qp_result)

    def test_passthrough_data_missing_version(self):
        """Test that passthrough_data without version raises ValueError for sampler_v2."""
        job = self._create_job()
        qp_result = QuantumProgramResult(
            data=[{"c": np.array([[0, 1]])}],
            metadata=Metadata(),
            passthrough_data={
                "post_processor": {
                    "context": "sampler_v2",
                    # Missing "version" field
                }
            },
        )

        # Should raise ValueError since version is required for sampler_v2 context
        with self.assertRaises(ValueError) as context:
            job._apply_post_processing(qp_result, None)

        self.assertIn("Could not determine a post-processor version", str(context.exception))

    def test_post_processing_error_propagation(self):
        """Test that post-processing errors are propagated."""
        job = self._create_job()
        qp_result = QuantumProgramResult(data=[{"c": np.array([[0, 1]])}], metadata=Metadata())

        # Use pre-registered failing processor as override
        with self.assertRaises(RuntimeError) as context:
            job._apply_post_processing(qp_result, SAMPLER_POST_PROCESSORS["failing_version"])

        self.assertIn("Test error", str(context.exception))

    def test_result_with_post_processor_parameter(self):
        """Test result() with post_processor parameter."""
        job = self._create_job()
        job._status = "DONE"

        # Mock the API response
        self.mock_api_client.job_results.return_value = '{"test": "data"}'

        # Mock decoder to return QuantumProgramResult
        mock_decoder = Mock()
        mock_decoder.decode.return_value = self.qp_result
        job._final_result_decoder = mock_decoder  # type: ignore[assignment]

        # Define test processor inline for this specific test
        def test_proc(qp_result): # pylint: disable=unused-argument
            return "param_result"

        result = job.result(post_processor=test_proc)

        self.assertEqual(result, "param_result")
