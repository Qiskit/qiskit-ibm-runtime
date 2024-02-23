# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for Estimator V2"""

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.circuit.library import RealAmplitudes, IQP
from qiskit.quantum_info import SparsePauliOp

from qiskit.primitives.containers import PrimitiveResult, PubResult, DataBin

from qiskit_ibm_runtime import EstimatorV2, Session
from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestEstimatorV2(IBMIntegrationTestCase):
    """Integration tests for Estimator V2 Primitive."""

    def setUp(self) -> None:
        super().setUp()
        self.backend = "ibmq_qasm_simulator"

    @run_integration_test
    def test_estimator_v2_session(self, service):
        """Verify correct results are returned"""
        backend = service.backend(self.backend)
        pass_mgr = generate_preset_pass_manager(backend=backend, optimization_level=1)

        psi1 = pass_mgr.run(RealAmplitudes(num_qubits=2, reps=2))
        psi2 = pass_mgr.run(RealAmplitudes(num_qubits=2, reps=3))

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)]).apply_layout(psi1.layout)
        H2 = SparsePauliOp.from_list([("IZ", 1)]).apply_layout(psi2.layout)
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)]).apply_layout(psi1.layout)

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
        theta3 = [1, 2, 3, 4, 5, 6]

        with Session(service, self.backend) as session:
            estimator = EstimatorV2(session=session)

            job = estimator.run([(psi1, H1, [theta1])])
            result = job.result()
            self._verify_result_type(result, num_pubs=1, shapes=[(1,)])

            job2 = estimator.run([(psi1, [H1, H3], [theta1, theta3]), (psi2, H2, theta2)])
            result2 = job2.result()
            self._verify_result_type(result2, num_pubs=2, shapes=[(2,), (1,)])

            job3 = estimator.run([(psi1, H1, theta1), (psi2, H2, theta2), (psi1, H3, theta3)])
            result3 = job3.result()
            self._verify_result_type(result3, num_pubs=3, shapes=[(1,), (1,), (1,)])

    @run_integration_test
    def test_estimator_v2_options(self, service):
        """Test V2 Estimator with different options."""
        backend = service.backend(self.backend)
        pass_mgr = generate_preset_pass_manager(backend=backend, optimization_level=1)
        circuit = pass_mgr.run(IQP([[6, 5, 3], [5, 4, 5], [3, 5, 1]]))
        observables = SparsePauliOp("X" * circuit.num_qubits).apply_layout(circuit.layout)

        estimator = EstimatorV2(backend=backend)
        estimator.options.resilience_level = 1
        estimator.options.optimization_level = 1
        # estimator.options.dynamical_decoupling = "XX"  # TODO: Re-enable when fixed
        estimator.options.seed_estimator = 42
        estimator.options.resilience.measure_noise_mitigation = True
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience.zne_noise_factors = [3, 5]
        estimator.options.resilience.zne_extrapolator = "linear"
        estimator.options.resilience.zne_stderr_threshold = 0.25
        estimator.options.resilience.pec_mitigation = False
        estimator.options.execution.shots = 4000
        estimator.options.execution.samples = 4
        estimator.options.execution.shots_per_sample = 1000
        estimator.options.execution.init_qubits = True
        estimator.options.execution.interleave_samples = True
        estimator.options.twirling.gates = True
        estimator.options.twirling.measure = True
        estimator.options.twirling.strategy = "active"

        job = estimator.run([(circuit, observables)])
        result = job.result()
        self._verify_result_type(result, num_pubs=1, shapes=[(1,)])
        self.assertEqual(result[0].metadata["shots"], 4000)
        for res_key in ["twirled_readout_errors", "zne_noise_factors"]:
            self.assertIn(res_key, result[0].metadata["resilience"])

    @run_integration_test
    def test_pec(self, service):
        """Test running with PEC."""
        backend = service.backend(self.backend)
        pass_mgr = generate_preset_pass_manager(backend=backend, optimization_level=1)
        circuit = pass_mgr.run(IQP([[6, 5, 3], [5, 4, 5], [3, 5, 1]]))
        observables = SparsePauliOp("X" * circuit.num_qubits).apply_layout(circuit.layout)

        estimator = EstimatorV2(backend=backend)
        estimator.options.resilience_level = 0
        estimator.options.optimization_level = 0
        estimator.options.resilience.pec_mitigation = True
        estimator.options.resilience.pec_max_overhead = 200
        estimator.options.simulator.set_backend(service.backends(simulator=False)[0])

        job = estimator.run([(circuit, observables)])
        result = job.result()
        self._verify_result_type(result, num_pubs=1, shapes=[(1,)])
        self.assertIn("sampling_overhead", result[0].metadata["resilience"])

    def _verify_result_type(self, result, num_pubs, shapes):
        """Verify result type."""
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), num_pubs)
        for idx, pub_result in enumerate(result):
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertTrue(pub_result.metadata)
            self.assertEqual(pub_result.data.evs.shape, shapes[idx])
            self.assertEqual(pub_result.data.stds.shape, shapes[idx])
