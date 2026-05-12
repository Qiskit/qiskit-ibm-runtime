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

"""Tests the decoder for the quantum program result model."""

import json
import unittest
from dataclasses import asdict
from datetime import datetime

import numpy as np
from ibm_quantum_schemas.common import TensorModel
from ibm_quantum_schemas.executor.version_0_1 import (
    ChunkPart,
    ChunkSpan,
    MetadataModel,
    QuantumProgramResultItemModel,
    QuantumProgramResultModel,
)
from qiskit.primitives import PrimitiveResult

from qiskit_ibm_runtime.options_models.sampler_options import SamplerOptions
from qiskit_ibm_runtime.results.quantum_program import (
    Metadata,
    QuantumProgramResult,
)
from qiskit_ibm_runtime.decoders.quantum_program.decoder import QuantumProgramResultDecoder

from ...ibm_test_case import IBMTestCase


class TestDecoder(IBMTestCase):
    """Tests the decoder for the quantum program result model."""

    def setUp(self):
        """Test level setup."""
        super().setUp()

        self.meas1 = np.array([[False], [True], [True]])
        self.meas2 = np.array([[True, True], [True, False], [False, False]])
        self.meas_flips = np.array([[False, False]])
        self.chunk_start = datetime(2025, 12, 30, 14, 10)
        self.chunk_stop = datetime(2025, 12, 30, 14, 15)

        chunk_model = ChunkSpan(
            start=self.chunk_start,
            stop=self.chunk_stop,
            parts=[ChunkPart(idx_item=0, size=1), ChunkPart(idx_item=1, size=1)],
        )
        metadata_model = MetadataModel(chunk_timing=[chunk_model])
        result1_model = QuantumProgramResultItemModel(
            results={"meas": TensorModel.from_numpy(self.meas1)}, metadata=None
        )
        result2_model = QuantumProgramResultItemModel(
            results={
                "meas": TensorModel.from_numpy(self.meas2),
                "measurement_flips.meas": TensorModel.from_numpy(self.meas_flips),
            },
            metadata=None,
        )
        result_model = QuantumProgramResultModel(
            data=[result1_model, result2_model], metadata=metadata_model
        )

        self.encoded = result_model.model_dump_json()

    def test_decoder(self):
        """Tests the decoder."""
        decoded = QuantumProgramResultDecoder.decode(self.encoded)

        self.assertTrue(np.array_equal(decoded[0]["meas"], self.meas1))
        self.assertTrue(np.array_equal(decoded[1]["meas"], self.meas2))
        self.assertTrue(np.array_equal(decoded[1]["measurement_flips.meas"], self.meas_flips))
        self.assertEqual(
            decoded.metadata.chunk_timing[0].start.replace(tzinfo=None), self.chunk_start
        )
        self.assertEqual(
            decoded.metadata.chunk_timing[0].stop.replace(tzinfo=None), self.chunk_stop
        )
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[0].idx_item, 0)
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[0].size, 1)
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[1].idx_item, 1)
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[1].size, 1)

    def test_no_schema_version(self):
        """Verify an error is raised if the encoded string does not specify any schema version."""
        encoded_as_json = json.loads(self.encoded)
        del encoded_as_json["schema_version"]
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "Missing schema version."):
            QuantumProgramResultDecoder.decode(encoded_as_str)

    def test_unknown_schema_version(self):
        """Verify an error is raised if the schema version specified does not exist."""
        encoded_as_json = json.loads(self.encoded)
        encoded_as_json["schema_version"] = "unknown"
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "No decoder found for schema version unknown."):
            QuantumProgramResultDecoder.decode(encoded_as_str)


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
        with self.assertRaises(ValueError):
            QuantumProgramResultDecoder._apply_post_processing(self.qp_result)

    def test_passthrough_data_unsupported_version(self):
        """A QuantumProgramResult with no post_processor version is returned unchanged."""
        self.qp_result._semantic_role = "sampler_v2"
        self.qp_result.passthrough_data["post_processor"]["version"] = "non-existing"
        with self.assertRaises(ValueError):
            QuantumProgramResultDecoder._apply_post_processing(self.qp_result)
