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

"""Unit tests for QuantumProgram to Sampler V2 decoder post-processing."""

import unittest
import numpy as np
from dataclasses import asdict

from qiskit.primitives import PrimitiveResult
from qiskit_ibm_runtime.options_models.sampler_options import SamplerOptions
from qiskit_ibm_runtime.quantum_program.result_decoders import QuantumProgramResultDecoder
from qiskit_ibm_runtime.quantum_program.quantum_program_result import (
    QuantumProgramResult,
    Metadata,
)


class TestDecoderPostProcessing(unittest.TestCase):
    """Test QuantumProgram to Sampler V2 decoder post-processing logic."""

    def setUp(self):
        """Set up test fixtures."""
        num_rands = 10
        num_shots_per_rand = 10
        meas_data_c1 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 2), dtype=np.uint8
        )
        meas_data_c2 = np.random.randint(
            0, 2, size=(num_rands, num_shots_per_rand, 3), dtype=np.uint8
        )

        options = SamplerOptions()
        options.twirling.enable_gates = True
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "options": asdict(options),
                "twirling": True,
                "meas_type": "classified",
            }
        }

        self.qp_result = QuantumProgramResult(
            data=[{"c1": meas_data_c1, "c2": meas_data_c2}],
            metadata=Metadata(),
            passthrough_data=passthrough_data,
        )

    def test_valid_result(self):
        """A QuantumProgramResult from a Sampler job should be post-processed."""
        self.qp_result._semantic_role = "sampler_v2"
        processed = QuantumProgramResultDecoder._apply_post_processing(self.qp_result)
        self.assertIsInstance(processed, PrimitiveResult)

    def test_no_semantic_role(self):
        """A QuantumProgramResult with unset semantic role is returned unchanged."""
        processed = QuantumProgramResultDecoder._apply_post_processing(self.qp_result)
        self.assertEqual(processed, self.qp_result)

    def test_unsupported_semantic_role(self):
        """A QuantumProgramResult with unsupported semantic role is returned unchanged."""
        self.qp_result._semantic_role = "unsupported_semantic_role"
        processed = QuantumProgramResultDecoder._apply_post_processing(self.qp_result)
        self.assertEqual(processed, self.qp_result)

    def test_passthrough_data_missing_version(self):
        """A QuantumProgramResult with no post_processor version is returned unchanged."""
        self.qp_result._semantic_role = "sampler_v2"
        self.qp_result.passthrough_data["post_processor"].pop("version")
        with self.assertLogs("qiskit_ibm_runtime", "ERROR") as context:
            processed = QuantumProgramResultDecoder._apply_post_processing(self.qp_result)

        self.assertEqual(processed, self.qp_result)
        self.assertIn("Unable to apply", str(context.records[0]))

    def test_passthrough_data_unsupported_version(self):
        """A QuantumProgramResult with no post_processor version is returned unchanged."""
        self.qp_result._semantic_role = "sampler_v2"
        self.qp_result.passthrough_data["post_processor"] = "non_existing"
        with self.assertLogs("qiskit_ibm_runtime", "ERROR") as context:
            processed = QuantumProgramResultDecoder._apply_post_processing(self.qp_result)

        self.assertEqual(processed, self.qp_result)
        self.assertIn("Unable to apply", str(context.records[0]))
