# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests the converters for the noise learner v3 model."""

import numpy as np
from pydantic import ValidationError
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import QubitSparsePauliList

from qiskit_ibm_runtime.noise_learner_v3.converters.version_0_1 import (
    noise_learner_v3_inputs_from_0_1,
    noise_learner_v3_inputs_to_0_1,
    noise_learner_v3_result_from_0_1,
    noise_learner_v3_result_to_0_1,
)
from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_result import (  # type: ignore[attr-defined]
    NoiseLearnerV3Result,
    NoiseLearnerV3Results,
)
from qiskit_ibm_runtime.options import NoiseLearnerV3Options

from ...ibm_test_case import IBMTestCase


class TestConverters(IBMTestCase):
    """Tests the converters for the noise learner v3 model."""

    def test_converting_inputs(self):
        """Tests converting inputs."""
        circuit = QuantumCircuit(3)
        with circuit.box():
            circuit.noop(1)
            circuit.cx(0, 2)
        with circuit.box():
            circuit.noop(2)
            circuit.cx(0, 1)

        instructions = [circuit[0], circuit[1]]

        options = NoiseLearnerV3Options()
        options.layer_pair_depths = [2, 4, 10]
        options.post_selection.enable = True
        options.post_selection.strategy = "edge"
        options.post_selection.x_pulse_type = "xslow"

        encoded = noise_learner_v3_inputs_to_0_1(instructions, options)
        decoded = noise_learner_v3_inputs_from_0_1(encoded)

        assert decoded == (instructions, options)

    def test_converting_results(self):
        """Tests converting results."""
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
        results = NoiseLearnerV3Results([result0, result1])

        encoded = noise_learner_v3_result_to_0_1(results)
        decoded = noise_learner_v3_result_from_0_1(encoded)
        for datum_in, datum_out in zip(results.data, decoded.data):
            assert datum_in._generators == datum_out._generators
            assert np.allclose(datum_in._rates, datum_out._rates)
            assert np.allclose(datum_in._rates_std, datum_out._rates_std)
            assert datum_in.metadata == datum_out.metadata

    def test_converting_invalid_results(self):
        """Test that converting results raises when results are invalid."""

        generators = [
            QubitSparsePauliList.from_list(["IX", "XX"]),
            QubitSparsePauliList.from_list(["XI"]),
        ]
        rates = [0.1, 0.2]

        metadata = {
            "input_options": {
                "shots_per_randomization": 3,
                "num_randomizations": 8,
                "layer_pair_depths": [0, 2, 6],
                "post_selection": {
                    "enable": True,
                    "strategy": "edge",
                    "x_pulse_type": "xslow",
                },
            }
        }

        for metadatum in [
            {"learning_protocol": "trex", "post_selection": {"strategy": "edge"}},
            {"learning_protocol": "trex", "post_selection": {"fraction_kept": 1.2}},
            {"learning_protocol": "trex", "post_selection": {"fraction_kept": -0.3}},
        ]:
            result = NoiseLearnerV3Result.from_generators(generators, rates, metadata=metadatum)
            results = NoiseLearnerV3Results([result], metadata)
            with self.assertRaisesRegex(
                ValidationError,
                "1 validation error for NoiseLearnerV3ResultModel",
            ):
                noise_learner_v3_result_to_0_1(results).model_dump()

        for metadatum in [
            {
                "learning_protocol": "trex",
                "post_selection": {"fraction_kept": {0: 0.1, 2: 0.3}},
            },
            {"learning_protocol": "lindblad", "post_selection": {"fraction_kept": 0.3}},
        ]:
            result = NoiseLearnerV3Result.from_generators(generators, rates, metadata=metadatum)
            results = NoiseLearnerV3Results([result], metadata)
            with self.assertRaisesRegex(
                ValidationError, "1 validation error for NoiseLearnerV3ResultModel"
            ):
                noise_learner_v3_result_to_0_1(results).model_dump()
