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

from qiskit_ibm_runtime.decoders.executor.decoder import (
    BaseClientSideResultDecoder,
    ExecutorResultDecoder,
)
from qiskit_ibm_runtime.results.quantum_program import Metadata, QuantumProgramResult

from ...ibm_test_case import IBMTestCase


def measurements():
    """Return the measurements and flips of two items, and the limits of the chunk they run in."""
    meas1 = np.array([[False], [True], [True]])
    meas2 = np.array([[True, True], [True, False], [False, False]])
    meas_flips = np.array([[False, False]])
    start = datetime(2025, 12, 30, 14, 10)
    stop = datetime(2025, 12, 30, 14, 15)

    return meas1, meas2, meas_flips, start, stop


def encoded_result():
    """Return the encoding of a result holding the measurements of two items."""
    meas1, meas2, meas_flips, start, stop = measurements()

    chunk_model = ChunkSpan(
        start=start,
        stop=stop,
        parts=[ChunkPart(idx_item=0, size=1), ChunkPart(idx_item=1, size=1)],
    )
    metadata_model = MetadataModel(chunk_timing=[chunk_model])
    result1_model = QuantumProgramResultItemModel(
        results={"meas": TensorModel.from_numpy(meas1)}, metadata=None
    )
    result2_model = QuantumProgramResultItemModel(
        results={
            "meas": TensorModel.from_numpy(meas2),
            "measurement_flips.meas": TensorModel.from_numpy(meas_flips),
        },
        metadata=None,
    )
    result_model = QuantumProgramResultModel(
        data=[result1_model, result2_model], metadata=metadata_model
    )

    return result_model.model_dump_json()


class TestDecoder(IBMTestCase):
    """Tests the decoder for the quantum program result model."""

    def test_decoder(self):
        """Tests the decoder."""
        meas1, meas2, meas_flips, start, stop = measurements()

        decoded = ExecutorResultDecoder.decode(encoded_result())

        assert np.array_equal(decoded[0]["meas"], meas1)
        assert np.array_equal(decoded[1]["meas"], meas2)
        assert np.array_equal(decoded[1]["measurement_flips.meas"], meas_flips)
        assert decoded.metadata.chunk_timing[0].start.replace(tzinfo=None) == start
        assert decoded.metadata.chunk_timing[0].stop.replace(tzinfo=None) == stop
        assert decoded.metadata.chunk_timing[0].parts[0].idx_item == 0
        assert decoded.metadata.chunk_timing[0].parts[0].size == 1
        assert decoded.metadata.chunk_timing[0].parts[1].idx_item == 1
        assert decoded.metadata.chunk_timing[0].parts[1].size == 1

    def test_no_schema_version(self):
        """Verify an error is raised if the encoded string does not specify any schema version."""
        encoded_as_json = json.loads(encoded_result())
        del encoded_as_json["schema_version"]
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "Missing schema version."):
            ExecutorResultDecoder.decode(encoded_as_str)

    def test_unknown_schema_version(self):
        """Verify an error is raised if the schema version specified does not exist."""
        encoded_as_json = json.loads(encoded_result())
        encoded_as_json["schema_version"] = "unknown"
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "No decoder found for schema version unknown."):
            ExecutorResultDecoder.decode(encoded_as_str)


class MyDecoder(BaseClientSideResultDecoder):
    """Custom `BaseClientSideResultDecoder` for tests."""

    SEMANTIC_ROLE = "foo"
    SUPPORTED_POST_PROCESSORS = {"v0.1": lambda x: x}


class TestBaseClientSideResultDecoder(IBMTestCase):
    """Test BaseClientSideResultDecoder decoder."""

    def test_is_applicable(self):
        """A decoder should not be applicable depending on input."""
        result = QuantumProgramResult(
            data=[{"dummy": np.array([1, 2, 3])}],
            metadata=Metadata(),
            passthrough_data={},
        )

        # Not applicable if the result has already been processed by a previous decoder.
        assert BaseClientSideResultDecoder.is_applicable({}) is False

        # Not applicable if the result does not have semantic role.
        assert BaseClientSideResultDecoder.is_applicable(result) is False

        # Not applicable if the result has a different semantic role.
        result._semantic_role = "not_foo"
        assert MyDecoder.is_applicable(result) is False

    def test_decode_raises(self):
        """A decoder `decode` method should raise depending on the input."""
        result = QuantumProgramResult(
            data=[{"dummy": np.array([1, 2, 3])}],
            metadata=Metadata(),
            passthrough_data={},
        )
        result._semantic_role = "foo"

        # Raises if version is not present.
        result.passthrough_data = {"post_processor": {}}
        with self.assertRaises(ValueError):
            MyDecoder.decode(result)

        # Raises if version is unsupported.
        result.passthrough_data = {"post_processor": {"version": "9.8"}}
        with self.assertRaises(ValueError):
            MyDecoder.decode(result)
