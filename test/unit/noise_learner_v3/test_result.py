import numpy as np

from samplomatic import InjectNoise, Twirl

from qiskit import QuantumCircuit
from qiskit.quantum_info import QubitSparsePauliList, PauliLindbladMap

from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_result import (
    NoiseLearnerV3Result,
    NoiseLearnerV3Results,
)

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3Result(IBMTestCase):
    """Tests the ``NoiseLearnerV3Result`` class."""

    def test_from_generators_valid_input(self):
        self.assertEqual(1, 2)