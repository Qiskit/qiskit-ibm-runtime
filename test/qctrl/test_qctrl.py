# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
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
from qiskit.quantum_info import Statevector, hellinger_fidelity
from qiskit.providers.jobstatus import JobStatus
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import RealAmplitudes
from qiskit.primitives.containers import PrimitiveResult, PubResult, DataBin, BitArray
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import (
    Sampler,
    SamplerV2,
    EstimatorV2,
    Batch,
    Options,
    Estimator,
    QiskitRuntimeService,
)
from qiskit_ibm_runtime.exceptions import IBMNotAuthorizedError

from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test
from ..utils import cancel_job_safe, bell

FIDELITY_THRESHOLD = 0.8
DIFFERENCE_THRESHOLD = 0.35


class TestV2PrimitivesQCTRL(IBMIntegrationTestCase):
    """Integration tests for V2 primitives using QCTRL."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = bell()
        self.backend = self.service.least_busy(simulator=False)

    @run_integration_test
    def test_sampler_v2_qctrl(self, service):
        """Test qctrl bell state with samplerV2"""
        shots = 1

        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=1)
        isa_circuit = pm.run(self.bell)

        with Batch(service, backend=self.backend):
            sampler = SamplerV2()

            result = sampler.run([isa_circuit], shots=shots).result()
            self._verify_sampler_result(result, num_pubs=1)

    @run_integration_test
    def test_estimator_v2_qctrl(self, service):
        """Test simple circuit with estimatorV2 using qctrl."""
        pass_mgr = generate_preset_pass_manager(backend=self.backend, optimization_level=1)

        psi1 = pass_mgr.run(RealAmplitudes(num_qubits=2, reps=2))
        psi2 = pass_mgr.run(RealAmplitudes(num_qubits=2, reps=3))

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)]).apply_layout(psi1.layout)
        H2 = SparsePauliOp.from_list([("IZ", 1)]).apply_layout(psi2.layout)
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)]).apply_layout(psi1.layout)

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
        theta3 = [1, 2, 3, 4, 5, 6]

        with Batch(service, self.backend):
            estimator = EstimatorV2()

            job = estimator.run([(psi1, H1, [theta1])])
            result = job.result()
            self._verify_estimator_result(result, num_pubs=1, shapes=[(1,)])

            job2 = estimator.run([(psi1, [H1, H3], [theta1, theta3]), (psi2, H2, theta2)])
            result2 = job2.result()
            self._verify_estimator_result(result2, num_pubs=2, shapes=[(2,), (1,)])

            job3 = estimator.run([(psi1, H1, theta1), (psi2, H2, theta2), (psi1, H3, theta3)])
            result3 = job3.result()
            self._verify_estimator_result(result3, num_pubs=3, shapes=[(1,), (1,), (1,)])

    def _verify_sampler_result(self, result, num_pubs, targets=None):
        """Verify result type."""
        self.assertIsInstance(result, PrimitiveResult)
        self.assertIsInstance(result.metadata, dict)
        self.assertEqual(len(result), num_pubs)
        for idx, pub_result in enumerate(result):
            # TODO: We need to update the following test to check `SamplerPubResult`
            # when the server side is upgraded to Qiskit 1.1.
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertIsInstance(pub_result.metadata, dict)
            if targets:
                self.assertIsInstance(result[idx].data.meas, BitArray)
                self._assert_allclose(result[idx].data.meas, targets[idx])

    def _verify_estimator_result(self, result, num_pubs, shapes):
        """Verify result type."""
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), num_pubs)
        for idx, pub_result in enumerate(result):
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertTrue(pub_result.metadata)
            self.assertEqual(pub_result.data.evs.shape, shapes[idx])
            self.assertEqual(pub_result.data.stds.shape, shapes[idx])


class TestQCTRL(IBMIntegrationTestCase):
    """Integration tests for QCTRL integration."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = bell()
        self.backend = "alt_canberra"

    def test_channel_strategy_parameter(self):
        """Test passing in channel strategy parameter for a q-ctrl instance."""
        service = QiskitRuntimeService(
            channel="ibm_cloud",
            url=self.dependencies.url,
            token=self.dependencies.token,
            instance=self.dependencies.instance,
            channel_strategy="q-ctrl",
        )
        self.assertTrue(service)

    def test_invalid_channel_strategy_parameter(self):
        """Test passing in invalid channel strategy parameter for a q-ctrl instance."""
        with self.assertRaises(IBMNotAuthorizedError):
            QiskitRuntimeService(
                channel="ibm_cloud",
                url=self.dependencies.url,
                token=self.dependencies.token,
                instance=self.dependencies.instance,
                channel_strategy=None,
            )

    @run_integration_test
    def test_cancel_qctrl_job(self, service):
        """Test canceling qctrl job."""
        with Batch(service, self.backend):
            options = Options(resilience_level=1)
            sampler = Sampler(options=options)

            job = sampler.run([self.bell] * 10)

        rjob = service.job(job.job_id())
        if not cancel_job_safe(rjob, self.log):
            return
        self.assertEqual(rjob.status(), JobStatus.CANCELLED)

    @run_integration_test
    def test_sampler_qctrl_bell(self, service):
        """Test qctrl bell state"""
        # Set shots for experiment
        shots = 1000

        # Create Bell test circuit
        bell_circuit = QuantumCircuit(2)
        bell_circuit.h(0)
        bell_circuit.cx(0, 1)

        # Add measurements for the sampler
        bell_circuit_sampler = bell_circuit.copy()
        bell_circuit_sampler.measure_active()

        # Execute circuit in a session with sampler
        with Batch(service, backend=self.backend):
            options = Options(resilience_level=1)
            sampler = Sampler(options=options)

            result = sampler.run(bell_circuit_sampler, shots=shots).result()
            results_dict = {
                "{0:02b}".format(key): value for key, value in result.quasi_dists[0].items()
            }  # convert keys to bitstrings

        ideal_result = {
            key: val / shots for key, val in Statevector(bell_circuit).probabilities_dict().items()
        }
        fidelity = hellinger_fidelity(results_dict, ideal_result)

        self.assertGreater(fidelity, FIDELITY_THRESHOLD)

    @run_integration_test
    def test_sampler_qctrl_ghz(self, service):
        """Test qctrl small GHZ"""
        shots = 1000
        num_qubits = 5
        ghz_circuit = QuantumCircuit(num_qubits)
        ghz_circuit.h(0)
        for i in range(num_qubits - 1):
            ghz_circuit.cx(i, i + 1)

        # Add measurements for the sampler
        ghz_circuit_sampler = ghz_circuit.copy()
        ghz_circuit_sampler.measure_active()

        # Execute circuit in a session with sampler
        with Batch(service, backend=self.backend):
            options = Options(resilience_level=1)
            sampler = Sampler(options=options)

            result = sampler.run(ghz_circuit_sampler, shots=shots).result()
            results_dict = {
                f"{{0:0{num_qubits}b}}".format(key): value
                for key, value in result.quasi_dists[0].items()
            }  # convert keys to bitstrings

        ideal_result = {
            key: val / shots for key, val in Statevector(ghz_circuit).probabilities_dict().items()
        }
        fidelity = hellinger_fidelity(results_dict, ideal_result)
        self.assertGreater(fidelity, FIDELITY_THRESHOLD)

    @run_integration_test
    def test_sampler_qctrl_superposition(self, service):
        """Test qctrl small superposition"""

        shots = 1000
        num_qubits = 5
        superposition_circuit = QuantumCircuit(num_qubits)
        superposition_circuit.h(range(num_qubits))

        # Add measurements for the sampler
        superposition_circuit_sampler = superposition_circuit.copy()
        superposition_circuit_sampler.measure_active()

        # Execute circuit in a session with sampler
        with Batch(service, backend=self.backend):
            options = Options(resilience_level=1)
            sampler = Sampler(options=options)

            result = sampler.run(superposition_circuit_sampler, shots=shots).result()
            results_dict = {
                f"{{0:0{num_qubits}b}}".format(key): value
                for key, value in result.quasi_dists[0].items()
            }  # convert keys to bitstrings

        ideal_result = {
            key: val / shots
            for key, val in Statevector(superposition_circuit).probabilities_dict().items()
        }
        fidelity = hellinger_fidelity(results_dict, ideal_result)
        self.assertGreater(fidelity, FIDELITY_THRESHOLD)

    @run_integration_test
    def test_sampler_qctrl_computational_states(self, service):
        """Test qctrl computational states"""
        shots = 1000
        num_qubits = 3
        computational_states_circuits = []
        for idx in range(2**num_qubits):
            circuit = QuantumCircuit(num_qubits)
            bitstring = f"{{0:0{num_qubits}b}}".format(idx)
            for bit_pos, bit in enumerate(
                bitstring[::-1]
            ):  # convert to little-endian (qiskit convention)
                if bit == "1":
                    circuit.x(bit_pos)
            computational_states_circuits.append(circuit)

        # Add measurements for the sampler
        computational_states_sampler_circuits = []
        for circuit in computational_states_circuits:
            circuit_sampler = circuit.copy()
            circuit_sampler.measure_all()
            computational_states_sampler_circuits.append(circuit_sampler)

        # Execute circuit in a session with sampler
        with Batch(service, backend=self.backend):
            options = Options(resilience_level=1)
            sampler = Sampler(options=options)

            result = sampler.run(computational_states_sampler_circuits, shots=shots).result()
            results_dict_list = [
                {f"{{0:0{num_qubits}b}}".format(key): value for key, value in quasis.items()}
                for quasis in result.quasi_dists
            ]  # convert keys to bitstrings

        ideal_results_list = [
            {key: val / shots for key, val in Statevector(circuit).probabilities_dict().items()}
            for circuit in computational_states_circuits
        ]
        fidelities = [
            hellinger_fidelity(results_dict, ideal_result)
            for results_dict, ideal_result in zip(results_dict_list, ideal_results_list)
        ]

        for fidelity in fidelities:
            self.assertGreater(fidelity, FIDELITY_THRESHOLD)

    @run_integration_test
    def test_estimator_qctrl_bell(self, service):
        """Test estimator qctrl bell state"""
        # Set shots for experiment
        shots = 1000

        # Create Bell test circuit
        bell_circuit = QuantumCircuit(2)
        bell_circuit.h(0)
        bell_circuit.cx(0, 1)

        # Measure some observables in the estimator
        observables = [SparsePauliOp("ZZ"), SparsePauliOp("IZ"), SparsePauliOp("ZI")]

        # Execute circuit in a session with estimator
        with Batch(service, backend=self.backend):
            estimator = Estimator()

            result = estimator.run(
                [bell_circuit] * len(observables), observables=observables, shots=shots
            ).result()

        ideal_result = [
            Statevector(bell_circuit).expectation_value(observable).real
            for observable in observables
        ]
        absolute_difference = [
            abs(obs_theory - obs_exp) for obs_theory, obs_exp in zip(ideal_result, result.values)
        ]
        # absolute_difference_dict = {
        #     obs.paulis[0].to_label(): diff for obs, diff in zip(observables, absolute_difference)
        # }

        for diff in absolute_difference:
            self.assertLess(diff, DIFFERENCE_THRESHOLD)

    @run_integration_test
    def test_estimator_qctrl_ghz(self, service):
        """Test estimator qctrl GHZ state"""
        shots = 1000
        num_qubits = 5
        ghz_circuit = QuantumCircuit(num_qubits)
        ghz_circuit.h(0)
        for i in range(num_qubits - 1):
            ghz_circuit.cx(i, i + 1)

        # Measure some observables in the estimator
        observables = [
            SparsePauliOp("Z" * num_qubits),
            SparsePauliOp("I" * (num_qubits - 1) + "Z"),
            SparsePauliOp("Z" + "I" * (num_qubits - 1)),
        ]

        # Execute circuit in a session with estimator
        with Batch(service, backend=self.backend):
            estimator = Estimator()

            result = estimator.run(
                [ghz_circuit] * len(observables), observables=observables, shots=shots
            ).result()

        ideal_result = [
            Statevector(ghz_circuit).expectation_value(observable).real
            for observable in observables
        ]
        absolute_difference = [
            abs(obs_theory - obs_exp) for obs_theory, obs_exp in zip(ideal_result, result.values)
        ]
        absolute_difference_dict = {
            obs.paulis[0].to_label(): diff for obs, diff in zip(observables, absolute_difference)
        }

        print(
            "absolute difference between theory and experiment expectation values: ",
            absolute_difference_dict,
        )
        for diff in absolute_difference:
            self.assertLess(diff, DIFFERENCE_THRESHOLD)

    @run_integration_test
    def test_estimator_qctrl_superposition(self, service):
        """Test estimator qctrl small superposition"""
        shots = 1000
        num_qubits = 4
        superposition_circuit = QuantumCircuit(num_qubits)
        superposition_circuit.h(range(num_qubits))

        # Measure some observables in the estimator
        obs_labels = [["I"] * num_qubits for _ in range(num_qubits)]
        for idx, obs in enumerate(obs_labels):
            obs[idx] = "Z"
        obs_labels = ["".join(obs) for obs in obs_labels]
        observables = [SparsePauliOp(obs) for obs in obs_labels]

        # Execute circuit in a session with estimator
        with Batch(service, backend=self.backend):
            estimator = Estimator()

            result = estimator.run(
                [superposition_circuit] * len(observables), observables=observables, shots=shots
            ).result()

        ideal_result = [
            Statevector(superposition_circuit).expectation_value(observable).real
            for observable in observables
        ]
        absolute_difference = [
            abs(obs_theory - obs_exp) for obs_theory, obs_exp in zip(ideal_result, result.values)
        ]
        # absolute_difference_dict = {
        #     obs.paulis[0].to_label(): diff for obs, diff in zip(observables, absolute_difference)
        # }

        for diff in absolute_difference:
            self.assertLess(diff, DIFFERENCE_THRESHOLD)

    @run_integration_test
    def test_estimator_qctrl_computational(self, service):
        """Test estimator qctrl computational states"""
        shots = 1000
        num_qubits = 3
        computational_states_circuits = []
        for idx in range(2**num_qubits):
            circuit = QuantumCircuit(num_qubits)
            bitstring = f"{{0:0{num_qubits}b}}".format(idx)
            for bit_pos, bit in enumerate(
                bitstring[::-1]
            ):  # convert to little-endian (qiskit convention)
                if bit == "1":
                    circuit.x(bit_pos)
            computational_states_circuits.append(circuit)

        # Measure some observables in the estimator
        obs_labels = [["I"] * num_qubits for _ in range(num_qubits)]
        for idx, obs in enumerate(obs_labels):
            obs[idx] = "Z"
        obs_labels = ["".join(obs) for obs in obs_labels]
        observables = [SparsePauliOp(obs) for obs in obs_labels]

        computational_states_circuits_estimator, observables_estimator = [], []
        for circuit in computational_states_circuits:
            computational_states_circuits_estimator += [circuit] * len(observables)
            observables_estimator += observables

        # Execute circuit in a session with estimator
        with Batch(service, self.backend):
            estimator = Estimator()
            result = estimator.run(
                computational_states_circuits_estimator,
                observables=observables_estimator,
                shots=shots,
            ).result()

        ideal_result = [
            Statevector(circuit).expectation_value(observable).real
            for circuit, observable in zip(
                computational_states_circuits_estimator, observables_estimator
            )
        ]
        absolute_difference = [
            abs(obs_theory - obs_exp) for obs_theory, obs_exp in zip(ideal_result, result.values)
        ]

        absolute_difference_dict = {}
        for idx in range(2**num_qubits):
            circuit = QuantumCircuit(num_qubits)
            bitstring = f"{{0:0{num_qubits}b}}".format(idx)

            absolute_difference_dict[bitstring] = {
                obs.paulis[0].to_label(): diff
                for obs, diff in zip(
                    observables_estimator[idx * len(observables) : (idx + 1) * len(observables)],
                    absolute_difference[idx * len(observables) : (idx + 1) * len(observables)],
                )
            }
        for diff in absolute_difference:
            self.assertLess(diff, DIFFERENCE_THRESHOLD)
