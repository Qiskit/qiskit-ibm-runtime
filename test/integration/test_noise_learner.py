# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for NoiseLearner."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_ibm_runtime import EstimatorV2, Session
from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.noise_learner import NoiseLearner
from qiskit_ibm_runtime.options import EstimatorOptions, NoiseLearnerOptions
from qiskit_ibm_runtime.results.noise_learner import LayerError, PauliLindbladError

from .case import IBMIntegrationTestCase

if TYPE_CHECKING:
    from qiskit_ibm_runtime import IBMBackend
    from qiskit_ibm_runtime.results.noise_learner import NoiseLearnerResult


def ecr_circuits() -> list[QuantumCircuit]:
    """Return two circuits of `ecr` gates, acting on two and three qubits."""
    c1 = QuantumCircuit(2)
    c1.ecr(0, 1)

    c2 = QuantumCircuit(3)
    c2.ecr(0, 1)
    c2.ecr(1, 2)
    c2.ecr(0, 1)

    return [c1, c2]


def default_input_options() -> dict:
    """Return the input options a noise learner defaults to."""
    return {
        "max_execution_time": None,
        "max_layers_to_learn": 4,
        "shots_per_randomization": 128,
        "num_randomizations": 32,
        "layer_pair_depths": [0, 1, 2, 4, 16, 32],
        "twirling_strategy": "active-accum",
    }


def assert_job_result(
    result: NoiseLearnerResult,
    backend: IBMBackend,
    expected_input_options: dict,
    n_results: int,
) -> None:
    """Assert that `result` is well formed and matches the expected input options."""
    assert len(result) >= n_results

    for datum in result.data:
        circuit = datum.circuit
        qubits = datum.qubits
        error = datum.error

        assert isinstance(datum, LayerError)
        assert isinstance(circuit, QuantumCircuit)
        assert isinstance(qubits, list)
        assert isinstance(error, PauliLindbladError)

        assert circuit.num_qubits == len(qubits)
        assert circuit.num_qubits == error.num_qubits

    metadata = deepcopy(result.metadata)
    assert metadata.pop("backend", None) == backend.name
    for key, val in expected_input_options.items():
        metadatum = metadata["input_options"].pop(key, None)
        assert val == metadatum
    assert metadata["input_options"] == {}


class TestIntegrationNoiseLearner(IBMIntegrationTestCase):
    """Integration tests for NoiseLearner."""

    def test_with_default_options(self):
        """Test noise learner with default options."""
        backend = self.service.backend(self.dependencies.qpu)
        options = NoiseLearnerOptions()
        learner = NoiseLearner(mode=backend, options=options)

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        circuits = pm.run(ecr_circuits())
        job = learner.run(circuits)
        job.wait_for_final_state()

        assert_job_result(job.result(), backend, default_input_options(), 3)

    def test_with_non_default_options(self):
        """Test noise learner with non-default options."""
        backend = self.service.backend(self.dependencies.qpu)
        options = NoiseLearnerOptions()
        options.max_layers_to_learn = 1
        options.layer_pair_depths = [0, 1]
        learner = NoiseLearner(mode=backend, options=options)

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        circuits = pm.run(ecr_circuits())
        job = learner.run(circuits)
        job.wait_for_final_state()

        input_options = default_input_options()
        input_options["max_layers_to_learn"] = 1
        input_options["layer_pair_depths"] = [0, 1]
        assert_job_result(job.result(), backend, input_options, 1)

    def test_with_no_layers(self):
        """Test noise learner when `max_layers_to_learn` is `0`."""
        backend = self.service.backend(self.dependencies.qpu)
        options = NoiseLearnerOptions()
        options.max_layers_to_learn = 0
        learner = NoiseLearner(mode=backend, options=options)

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        circuits = pm.run(ecr_circuits())
        job = learner.run(circuits)
        job.wait_for_final_state()

        assert job.result().data == []

        input_options = default_input_options()
        input_options["max_layers_to_learn"] = 0
        assert_job_result(job.result(), backend, input_options, 0)

    def test_learner_plus_estimator(self):
        """Test feeding noise learner data to estimator."""
        backend = self.service.backend(self.dependencies.qpu)
        options = EstimatorOptions()
        options.resilience.zne_mitigation = True
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

        with Session(backend) as session:
            learner = NoiseLearner(mode=session, options=options)
            try:
                learner_job = learner.run(ecr_circuits())
            except IBMInputValueError as ex:
                if "The instruction ecr on qubits (0, 1) is not supported" in ex.message:
                    self.skipTest("Backend does not meet requirements")
            noise_model = learner_job.result()
            assert len(noise_model) == 3

            estimator = EstimatorV2(mode=session, options=options)
            estimator.options.resilience.layer_noise_model = noise_model.data

            estimator_job = estimator.run(pubs)
            result = estimator_job.result()

            noise_model_metadata = result.metadata["resilience"]["layer_noise_model"]
            for nm0 in noise_model:
                match_found = False
                for nm1 in noise_model_metadata:
                    if nm0.circuit == nm1.circuit:
                        assert nm0.qubits == nm1.qubits
                        assert nm0.error.generators == nm1.error.generators
                        assert nm0.error.rates.tolist() == nm1.error.rates.tolist()
                        match_found = True
                assert match_found
