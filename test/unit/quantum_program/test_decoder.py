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

from datetime import datetime
import json
import numpy as np

from ibm_quantum_schemas.models.executor.version_0_1.models import (
    QuantumProgramResultModel,
    QuantumProgramResultItemModel,
    ChunkPart,
    ChunkSpan,
    MetadataModel,
)
from ibm_quantum_schemas.models.tensor_model import TensorModel

from qiskit_ibm_runtime.quantum_program.quantum_program_decoders import QuantumProgramResultDecoder

from ...ibm_test_case import IBMTestCase


class TestDecoder(IBMTestCase):
    """Tests the decoder for the quantum program result model."""

    def setUp(self):
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
        self.assertEqual(decoded.metadata.chunk_timing[0].start, self.chunk_start)
        self.assertEqual(decoded.metadata.chunk_timing[0].stop, self.chunk_stop)
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[0].idx_item, 0)
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[0].size, 1)
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[1].idx_item, 1)
        self.assertEqual(decoded.metadata.chunk_timing[0].parts[1].size, 1)

    def test_no_schema_version(self):
        """Verify that an error is raised if the encoded string
        does not specify any schema version."""
        encoded_as_json = json.loads(self.encoded)
        del encoded_as_json["schema_version"]
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "Missing schema version."):
            QuantumProgramResultDecoder.decode(encoded_as_str)

    def test_unknown_schema_version(self):
        """Verify that an error is raised if the schema version specified in the encoded string
        does not exist."""
        encoded_as_json = json.loads(self.encoded)
        encoded_as_json["schema_version"] = "unknown"
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "No decoder found for schema version unknown."):
            QuantumProgramResultDecoder.decode(encoded_as_str)
