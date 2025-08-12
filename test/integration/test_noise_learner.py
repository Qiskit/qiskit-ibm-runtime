# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for NoiseLearner."""

from copy import deepcopy

from qiskit.circuit import QuantumCircuit

from qiskit_ibm_runtime import RuntimeJobV2, Session, EstimatorV2
from qiskit_ibm_runtime.noise_learner import NoiseLearner
from qiskit_ibm_runtime.utils.noise_learner_result import PauliLindbladError, LayerError
from qiskit_ibm_runtime.options import NoiseLearnerOptions, EstimatorOptions

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationNoiseLearner(IBMIntegrationTestCase):
    """Integration tests for NoiseLearner."""

    def setUp(self) -> None:
        super().setUp()

        self._backend = self.service.backend(self.dependencies.qpu)

        c1 = QuantumCircuit(2)
        c1.ecr(0, 1)

        c2 = QuantumCircuit(3)
        c2.ecr(0, 1)
        c2.ecr(1, 2)
        c2.ecr(0, 1)

        self.circuits = [c1, c2]

        self.default_input_options = {
            "max_execution_time": None,
            "max_layers_to_learn": 4,
            "shots_per_randomization": 128,
            "num_randomizations": 32,
            "layer_pair_depths": [0, 1, 2, 4, 16, 32],
            "twirling_strategy": "active-accum",
        }

    @run_integration_test
    def test_with_default_options(self, service):  # pylint: disable=unused-argument
        """Test noise learner with default options."""
        options = NoiseLearnerOptions()
        learner = NoiseLearner(mode=self._backend, options=options)

        job = learner.run(self.circuits)

        self._verify(job, self.default_input_options, 3)

    @run_integration_test
    def test_with_non_default_options(self, service):  # pylint: disable=unused-argument
        """Test noise learner with non-default options."""
        options = NoiseLearnerOptions()
        options.max_layers_to_learn = 1
        options.layer_pair_depths = [0, 1]
        learner = NoiseLearner(mode=self._backend, options=options)

        job = learner.run(self.circuits)

        input_options = deepcopy(self.default_input_options)
        input_options["max_layers_to_learn"] = 1
        input_options["layer_pair_depths"] = [0, 1]
        self._verify(job, input_options, 1)

    @run_integration_test
    def test_with_no_layers(self, service):  # pylint: disable=unused-argument
        """Test noise learner when `max_layers_to_learn` is `0`."""
        options = NoiseLearnerOptions()
        options.max_layers_to_learn = 0
        learner = NoiseLearner(mode=self._backend, options=options)

        job = learner.run(self.circuits)

        self.assertEqual(job.result().data, [])

        input_options = deepcopy(self.default_input_options)
        input_options["max_layers_to_learn"] = 0
        self._verify(job, input_options, 0)

    @run_integration_test
    def test_learner_plus_estimator(self, service):  # pylint: disable=unused-argument
        """Test feeding noise learner data to estimator."""
        options = EstimatorOptions()
        options.resilience.zne_mitigation = True  # pylint: disable=assigning-non-slot
        options.resilience.zne.amplifier = "pea"
        options.resilience.layer_noise_learning.layer_pair_depths = [0, 1]

        circuit = QuantumCircuit(3)
        circuit.ecr(0, 1)
        circuit.ecr(1, 2)
        circuit.ecr(1, 2)
        circuit.ecr(0, 1)
        circuit.ecr(0, 1)
        circuit.ecr(0, 1)

        pubs = [(circuit, "Z" * circuit.num_qubits)]

        with Session(self._backend) as session:
            learner = NoiseLearner(mode=session, options=options)
            learner_job = learner.run(self.circuits)
            noise_model = learner_job.result()
            self.assertEqual(len(noise_model), 3)

            estimator = EstimatorV2(mode=session, options=options)
            estimator.options.resilience.layer_noise_model = noise_model.data

            estimator_job = estimator.run(pubs)
            result = estimator_job.result()

            noise_model_metadata = result.metadata["resilience"]["layer_noise_model"]
            for nm0 in noise_model:
                match_found = False
                for nm1 in noise_model_metadata:
                    if nm0.circuit == nm1.circuit:
                        self.assertEqual(nm0.qubits, nm1.qubits)
                        self.assertEqual(nm0.error.generators, nm1.error.generators)
                        self.assertEqual(nm0.error.rates.tolist(), nm1.error.rates.tolist())
                        match_found = True
                self.assertTrue(match_found)

    def _verify(self, job: RuntimeJobV2, expected_input_options: dict, n_results: int) -> None:
        job.wait_for_final_state()

        result = job.result()
        self.assertEqual(len(result), n_results)

        for datum in result.data:
            circuit = datum.circuit
            qubits = datum.qubits
            error = datum.error

            self.assertIsInstance(datum, LayerError)
            self.assertIsInstance(circuit, QuantumCircuit)
            self.assertIsInstance(qubits, list)
            self.assertIsInstance(error, PauliLindbladError)

            self.assertEqual(circuit.num_qubits, len(qubits))
            self.assertEqual(circuit.num_qubits, error.num_qubits)

        metadata = deepcopy(result.metadata)
        self.assertEqual(metadata.pop("backend", None), self._backend.name)
        for key, val in expected_input_options.items():
            metadatum = metadata["input_options"].pop(key, None)
            self.assertEqual(val, metadatum)
        self.assertEqual(metadata["input_options"], {})
