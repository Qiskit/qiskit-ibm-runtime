# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for job functions using real runtime service."""

from qiskit import QuantumCircuit

from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime import Session, Sampler, Options, Estimator
from qiskit_ibm_runtime.fake_provider import FakeManila
from qiskit_ibm_runtime.exceptions import RuntimeJobFailureError

from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test, production_only


class TestIntegrationOptions(IBMIntegrationTestCase):
    """Integration tests for options."""

    @run_integration_test
    def test_noise_model(self, service):
        """Test running with noise model."""
        backend = service.get_backend("ibmq_qasm_simulator")
        self.log.info("Using backend %s", backend.name)

        fake_backend = FakeManila()
        noise_model = NoiseModel.from_backend(fake_backend)

        circ = QuantumCircuit(1, 1)
        circ.x(0)
        circ.measure_all(add_bits=False)

        options = Options(
            simulator={
                "noise_model": noise_model,
                "basis_gates": fake_backend.configuration().basis_gates,
                "coupling_map": fake_backend.configuration().coupling_map,
                "seed_simulator": 42,
            },
            resilience_level=0,
        )

        with Session(service=service, backend=backend):
            sampler = Sampler(options=options)
            job1 = sampler.run(circ)
            self.log.info("Runtime job %s submitted.", job1.job_id())
            result1 = job1.result()
            # We should get both 0 and 1 if there is noise.
            self.assertEqual(len(result1.quasi_dists[0].keys()), 2)

            job2 = sampler.run(circ)
            self.log.info("Runtime job %s submitted.", job2.job_id())
            result2 = job2.result()
            # We should get both 0 and 1 if there is noise.
            self.assertEqual(len(result2.quasi_dists[0].keys()), 2)
            # The results should be the same because we used the same seed.
            self.assertEqual(result1.quasi_dists, result2.quasi_dists)

    @run_integration_test
    def test_simulator_transpile(self, service):
        """Test simulator transpile options."""
        backend = service.backend("ibmq_qasm_simulator")
        self.log.info("Using backend %s", backend.name)

        circ = QuantumCircuit(2, 2)
        circ.cx(0, 1)
        circ.measure_all(add_bits=False)
        obs = SparsePauliOp.from_list([("IZ", 1)])

        option_vars = [
            Options(simulator={"coupling_map": []}),
            Options(simulator={"basis_gates": ["foo"]}),
        ]

        with Session(service=service, backend=backend):
            for opt in option_vars:
                with self.subTest(opt=opt):
                    sampler = Sampler(options=opt)
                    job1 = sampler.run(circ)
                    self.log.info("Runtime job %s submitted.", job1.job_id())
                    with self.assertRaises(RuntimeJobFailureError):
                        job1.result()
                    # TODO: Re-enable when ntc-1651 is fixed
                    # self.assertIn("TranspilerError", err.exception.message)

                    estimator = Estimator(options=opt)
                    job2 = estimator.run(circ, observables=obs)
                    with self.assertRaises(RuntimeJobFailureError):
                        job2.result()
                    # TODO: Re-enable when ntc-1651 is fixed
                    # self.assertIn("TranspilerError", err.exception.message)

    @run_integration_test
    def test_unsupported_input_combinations(self, service):
        """Test that when resilience_level==3, and backend is a simulator,
        a coupling map is required."""
        circ = QuantumCircuit(1)
        obs = SparsePauliOp.from_list([("I", 1)])
        options = Options()
        options.resilience_level = 3
        backend = service.backend("ibmq_qasm_simulator")
        with Session(service=service, backend=backend) as session:
            with self.assertRaises(ValueError) as exc:
                inst = Estimator(session=session, options=options)
                inst.run(circ, observables=obs)
            self.assertIn("a coupling map is required.", str(exc.exception))

    @run_integration_test
    def test_default_resilience_settings(self, service):
        """Test that correct default resilience settings are used."""
        circ = QuantumCircuit(1)
        obs = SparsePauliOp.from_list([("I", 1)])
        options = Options(resilience_level=2)
        backend = service.backend("ibmq_qasm_simulator")
        with Session(service=service, backend=backend) as session:
            inst = Estimator(session=session, options=options)
            job = inst.run(circ, observables=obs)
            self.assertEqual(job.inputs["resilience_settings"]["noise_factors"], [1, 3, 5])
            self.assertEqual(
                job.inputs["resilience_settings"]["extrapolator"], "LinearExtrapolator"
            )

        options = Options(resilience_level=1)
        with Session(service=service, backend=backend) as session:
            inst = Estimator(session=session, options=options)
            job = inst.run(circ, observables=obs)
            self.assertNotIn("noise_factors", job.inputs["resilience_settings"])
            self.assertNotIn("extrapolator", job.inputs["resilience_settings"])

    @production_only
    @run_integration_test
    def test_all_resilience_levels(self, service):
        """Test that all resilience_levels are recognized correctly
        by checking their values in the metadata"""
        resilience_values = {
            0: "variance",
            1: "readout_mitigation_num_twirled_circuits",
            2: "zne",
            3: "standard_error",
        }
        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        h_1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])

        backend = service.backend("ibmq_qasm_simulator")
        options = Options()
        options.simulator.coupling_map = [[0, 1], [1, 0]]

        for level, value in resilience_values.items():
            options.resilience_level = level
            inst = Estimator(backend=backend, options=options)
            theta1 = [0, 1, 1, 2, 3, 5]
            result = inst.run(
                circuits=[psi1], observables=[h_1], parameter_values=[theta1]
            ).result()
            metadata = result.metadata[0]
            self.assertTrue(value in metadata)
