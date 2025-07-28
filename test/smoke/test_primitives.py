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

"""Testing simple primitive jobs for smoke tests."""

from qiskit import QuantumCircuit
from qiskit.primitives import PrimitiveResult
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.circuit.library import real_amplitudes
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import SamplerV2, EstimatorV2
from qiskit_ibm_runtime.noise_learner import NoiseLearner
from qiskit_ibm_runtime.utils.noise_learner_result import NoiseLearnerResult
from qiskit_ibm_runtime.options import NoiseLearnerOptions
from ..ibm_test_case import IBMIntegrationTestCase


class TestSmokePrimitives(IBMIntegrationTestCase):
    """Smoke tests."""

    def setUp(self):
        super().setUp()
        self._backend = self.service.backend(self.dependencies.qpu)
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)
        # bell circuit
        bell = QuantumCircuit(2, name="Bell")
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()
        self._isa_bell = pm.run(bell)
        # estimator circuit
        self._psi1 = pm.run(real_amplitudes(num_qubits=2, reps=2))
        # noise learner circuit
        c1 = QuantumCircuit(2)
        c1.ecr(0, 1)
        c2 = QuantumCircuit(3)
        c2.ecr(0, 1)
        c2.ecr(1, 2)
        c2.ecr(0, 1)
        self._circuits = [c1, c2]

    def test_sampler(self):
        """Test sampler job."""
        sampler = SamplerV2(mode=self._backend)
        sampler.options.default_shots = 4096
        sampler.options.execution.init_qubits = True
        sampler.options.execution.rep_delay = 0.00025
        job = sampler.run([self._isa_bell])
        self.assertIsInstance(job.result(), PrimitiveResult)

    def test_estimator(self):
        """Test estimator job."""
        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)]).apply_layout(
            self._psi1.layout
        )
        theta1 = [0, 1, 1, 2, 3, 5]

        estimator = EstimatorV2(mode=self._backend)
        job = estimator.run([(self._psi1, H1, [theta1])])
        self.assertIsInstance(job.result(), PrimitiveResult)

    def test_noise_learner(self):
        """Test noise learner job."""
        options = NoiseLearnerOptions()
        learner = NoiseLearner(mode=self._backend, options=options)
        job = learner.run(self._circuits)
        self.assertIsInstance(job.result(), NoiseLearnerResult)
