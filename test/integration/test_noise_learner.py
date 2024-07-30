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

import numpy as np
from copy import deepcopy

from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit.providers.jobstatus import JobStatus

from qiskit_ibm_runtime import RuntimeJob, Session
from qiskit_ibm_runtime.noise_learner import NoiseLearner
from qiskit_ibm_runtime.options import NoiseLearnerOptions

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationNoiseLearner(IBMIntegrationTestCase):
    """Integration tests for NoiseLearner."""

    def setUp(self) -> None:
        super().setUp()
        self.backend = "ibmq_qasm_simulator"

        c1 = QuantumCircuit(2)
        c1.cx(0, 1)

        c2 = QuantumCircuit(3)
        c2.cx(0, 1)
        c2.cx(1, 2)
        c2.cx(0, 1)

        self.circuits = [c1, c2]

        self.default_input_options = {
            "max_execution_time": None,
            "max_layers_to_learn": 4,
            "shots_per_randomization": 128,
            "num_randomizations": 32,
            "layer_pair_depths": [0, 1],
            "twirling_strategy": "active-accum",
        }

    @run_integration_test
    def test_with_default_options(self, service):
        """Test noise learner with default options."""
        options = NoiseLearnerOptions()

        learner = NoiseLearner(mode=self.backend, options=options)
        job = learner.run(self.circuits)
        self._verify(job, self.default_input_options)

    @run_integration_test
    def test_with_non_default_options(self, service):
        """Test noise learner with non-default options."""
        options = NoiseLearnerOptions()
        options.max_layers_to_learn = 1
        options.layer_pair_depths = [0, 1]

        learner = NoiseLearner(mode=self.backend, options=options)
        job = learner.run(self.circuits)

        input_options = deepcopy(self.default_input_options)
        input_options["max_layers_to_learn"] = 1
        input_options["layer_pair_depths"] = [0, 1]
        self._verify(job, input_options)

    @run_integration_test
    def test_in_session(self, service):
        """Test noise learner with non-default options."""
        options = NoiseLearnerOptions()
        options.max_layers_to_learn = 1
        options.layer_pair_depths = [0, 1]
        
        input_options = deepcopy(self.default_input_options)
        input_options["max_layers_to_learn"] = 1
        input_options["layer_pair_depths"] = [0, 1]

        with Session(service, self.backend) as session:
            options.twirling_strategy = "all"
            learner1 = NoiseLearner(mode=session, options=options)
            job1 = learner1.run(self.circuits)
            
            input_options["twirling_strategy"] = "all"
            self._verify(job1, input_options)

            options.twirling_strategy = "active-circuit"
            learner2 = NoiseLearner(mode=session, options=options)
            job2 = learner2.run(self.circuits)
            
            input_options["twirling_strategy"] = "active-circuit"
            self._verify(job2, input_options)

    def _verify(self, job: RuntimeJob, expected_input_options: dict):
        job.wait_for_final_state()
        self.assertEqual(job.status(), JobStatus.DONE, job.error_message())

        result = job.result()
        for datum in result.data:
            circuit = datum.circuit
            qubits = datum.qubits
            generators = datum.generators
            rates = datum.rates

            self.assertIsInstance(circuit, QuantumCircuit)
            self.assertIsInstance(qubits, list)
            self.assertIsInstance(generators, PauliList)
            self.assertIsInstance(rates, np.ndarray)

            self.assertEqual(circuit.num_qubits, len(qubits))
            self.assertEqual(circuit.num_qubits, generators.num_qubits)
            self.assertEqual(len(generators), len(rates))

        metadata = deepcopy(result.metadata)
        self.assertEqual(metadata.pop("backend", None), self.backend.name)
        for key, val in expected_input_options.items():
            metadatum = metadata["input_options"].pop(key, None)
            self.assertEqual(val, metadatum)
        self.assertEqual(metadata["input_options"], {})

