from __future__ import annotations

import numpy as np
from ddt import ddt
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator

# TODO: This import is not yet available. Maybe we can directly skip this,
# once local mode of Estimator is supported
from qiskit_ibm_runtime.sim_executor import SimExecutor

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases


@ddt
class TestSampler(IBMTestCase):
    def setUp(self):
        super().setUp()
        self.backend = FakeManilaV2()

    def test_simple_mirror_circuit_correct_evs(self):
        circuit = make_mirror_circuit_with_phases(self.backend)

        # TODO: I think we need to explicitly define parameters in order to write assertion on EVs
        parameters = np.random.random((2, 3) + (circuit.num_parameters,))

        estimator = EstimatorV2(self.backend)
        estimator._executor = SimExecutor(AerSimulator())

        observable = SparsePauliOp("ZZ")
        pub = (circuit, parameters, [observable])
        result = estimator.run([pub]).result()

        statevector_estimator = StatevectorEstimator()
        statevector_result = statevector_estimator.run([pub]).result()

        # TODO: make this a class assertion + check for proximity rather than equivalence
        assert result[0].evs[0] == statevector_result[0].evs[0]
