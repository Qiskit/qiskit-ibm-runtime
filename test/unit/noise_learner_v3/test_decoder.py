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

"""Tests the decoder for the noise learner v3 model."""

import json
import numpy as np
from qiskit.quantum_info import QubitSparsePauliList

from qiskit_ibm_runtime.noise_learner_v3.converters.version_0_1 import (
    noise_learner_v3_result_to_0_1,
)
from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_decoders import (
    NoiseLearnerV3ResultDecoder,
)
from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_result import (  # type: ignore[attr-defined]
    NoiseLearnerV3Result,
    NoiseLearnerV3Results,
)

from ...ibm_test_case import IBMTestCase


class TestDecoder(IBMTestCase):
    """Tests the decoder for the noise learner v3 model."""

    def setUp(self):
        super().setUp()

        generators = [
            QubitSparsePauliList.from_list(["IX", "XX"]),
            QubitSparsePauliList.from_list(["XI"]),
        ]
        rates = [0.1, 0.2]
        rates_std = [0.01, 0.02]

        metadatum0 = {
            "learning_protocol": "trex",
            "post_selection": {"fraction_kept": 1},
        }
        result0 = NoiseLearnerV3Result.from_generators(generators, rates, rates_std, metadatum0)

        metadatum1 = {
            "learning_protocol": "lindblad",
            "post_selection": {"fraction_kept": {0: 1, 4: 1}},
        }
        result1 = NoiseLearnerV3Result.from_generators(generators, rates, metadata=metadatum1)
        self.results = NoiseLearnerV3Results([result0, result1])

        self.encoded = noise_learner_v3_result_to_0_1(self.results).model_dump_json()

    def test_decoder(self):
        """Tests the decoder."""
        decoded = NoiseLearnerV3ResultDecoder.decode(self.encoded)
        for datum_in, datum_out in zip(self.results.data, decoded.data):
            assert datum_in._generators == datum_out._generators
            assert np.allclose(datum_in._rates, datum_out._rates)
            assert np.allclose(datum_in._rates_std, datum_out._rates_std)
            assert datum_in.metadata == datum_out.metadata

    def test_no_schema_version(self):
        """Verify that an error is raised if the encoded string
        does not specify any schema version."""
        encoded_as_json = json.loads(self.encoded)
        del encoded_as_json["schema_version"]
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "Missing schema version."):
            NoiseLearnerV3ResultDecoder.decode(encoded_as_str)

    def test_unknown_schema_version(self):
        """Verify that an error is raised if the schema version specified in the encoded string
        does not exist."""
        encoded_as_json = json.loads(self.encoded)
        encoded_as_json["schema_version"] = "unknown"
        encoded_as_str = json.dumps(encoded_as_json)
        with self.assertRaisesRegex(ValueError, "No decoder found for schema version unknown."):
            NoiseLearnerV3ResultDecoder.decode(encoded_as_str)
