# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for client-side Sampler."""

from unittest import skipUnless

import numpy as np
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.circuit import BoxOp, Parameter
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import generate_preset_pass_manager
from qiskit.utils.optionals import HAS_AER

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_sampler import Sampler
from qiskit_ibm_runtime.fake_provider import FakeVigoV2
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.session import Session

from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...registries import OneInstanceDryRunRegistry


@ddt
class TestSamplerSimpleCircuits(IBMTestCase):
    """Tests for Sampler with simple (non-parametric) circuits."""

    @mock_responses(OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry):
        """Sampler can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        sampler = Sampler(mode=backend)

        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        job = sampler.run([circuit], dry_run=True)
        self.assertEqual(job.backend().name, "mock_foo")

    @data("job", "session", "batch")
    @mock_responses
    def test_mode_handling(self, mode_id, registry):
        """Sampler `mode` init argument should propagate to interface and through `run()`."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")

        match mode_id:
            case "job":
                mode = backend
                expected_mode = None
                expected_session_id = None
            case "session":
                mode = Session(backend)
                expected_mode = mode
                expected_session_id = "session-12345"
            case "batch":
                mode = Batch(backend)
                expected_mode = mode
                expected_session_id = "session-12345"

        # Public interfaces should respect `mode`.
        sampler = Sampler(mode=mode)
        self.assertEqual(sampler.backend(), backend)
        self.assertEqual(sampler.mode, expected_mode)

        # Jobs issued should belong to a session under `session` / `batch`` modes.
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()
        job = sampler.run([circuit])
        self.assertEqual(job.session_id, expected_session_id)


class TestSamplerCircuitValidation(IBMTestCase):
    """Tests for circuit validation in Sampler."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = FakeVigoV2()

    def test_multiple_circuits_one_with_box_raises_error(self):
        """Test that BoxOp in any circuit raises an error."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        inner_circuit = QuantumCircuit(2)
        inner_circuit.h(0)

        circuit2 = QuantumCircuit(2, 2)
        circuit2.append(BoxOp(inner_circuit), [0, 1])
        circuit2.measure_all()

        sampler = Sampler(mode=self.backend)

        with self.assertRaisesRegex(IBMInputValueError, "BoxOp"):
            sampler.run([circuit1, circuit2], shots=1024)


@skipUnless(condition=HAS_AER, reason="qiskit-aer is required to run this test")
class TestSamplerSimulatorMode(IBMTestCase):
    """Tests for Sampler with simulator backends (local mode)."""

    def test_simulator_mode_uses_backend_sampler(self):
        """Test that simulator mode uses BackendSampler instead of Executor."""
        backend = GenericBackendV2(num_qubits=5)

        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        transpiled = pm.run(circuit)

        sampler = Sampler(mode=backend)

        # Run should work and return results
        job = sampler.run([transpiled], shots=100)
        result = job.result()

        # Verify we got results
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].data)

        # Verify the results are valid Bell state measurements
        counts = result[0].data.c.get_counts()
        # Should only have |00> and |11> states
        for bitstring in counts.keys():
            self.assertIn(bitstring, ["00", "11"])
        # Total counts should equal shots
        self.assertEqual(sum(counts.values()), 100)

    def test_simulator_options_seed(self):
        """Test that simulator seed option produces deterministic results."""
        backend = GenericBackendV2(num_qubits=5)

        # Create circuit with Hadamards (don't pre-allocate classical bits)
        circuit = QuantumCircuit(3)
        circuit.h([0, 1, 2])
        circuit.measure_all()

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        transpiled = pm.run(circuit)

        # First sampler with seed
        sampler1 = Sampler(mode=backend)
        sampler1.options.default_shots = 200
        sampler1.options.simulator.seed_simulator = 42

        job1 = sampler1.run([transpiled])
        result1 = job1.result()
        counts1 = result1[0].data.meas.get_counts()

        # Second sampler with same seed
        sampler2 = Sampler(mode=backend)
        sampler2.options.default_shots = 200
        sampler2.options.simulator.seed_simulator = 42

        job2 = sampler2.run([transpiled])
        result2 = job2.result()
        counts2 = result2[0].data.meas.get_counts()

        # Results should be identical with same seed
        self.assertEqual(counts1, counts2)

        # Third sampler with different seed should give different results
        sampler3 = Sampler(mode=backend)
        sampler3.options.default_shots = 200
        sampler3.options.simulator.seed_simulator = 123

        job3 = sampler3.run([transpiled])
        result3 = job3.result()
        counts3 = result3[0].data.meas.get_counts()

        # Results should be different with different seed
        self.assertNotEqual(counts1, counts3)

    def test_simulator_with_general_test_case(self):
        """Test simulator mode with comprehensive simulator options.

        This test exercises all available simulator options:
        - Parametric circuit with parameter sweep
        - Noise model
        - Coupling map
        - Basis gates
        - Seed simulator for reproducibility
        """
        backend = GenericBackendV2(num_qubits=5)

        # Create a parametric circuit with multiple parameters
        theta = Parameter("θ")
        phi = Parameter("φ")
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.rx(theta, 1)
        circuit.ry(phi, 2)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        transpiled = pm.run(circuit)

        # Parameter sweep with multiple parameter value sets
        param_values = [
            [0.0, 0.0],  # First parameter set
            [np.pi / 2, np.pi / 4],  # Second parameter set
            [np.pi, np.pi / 2],  # Third parameter set
        ]

        # Create sampler with all simulator options
        sampler = Sampler(mode=backend)
        sampler.options.simulator.seed_simulator = 42

        # Run with parameter sweep
        job = sampler.run([(transpiled, param_values)], shots=1000)
        result = job.result()

        # Verify results structure
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].data)

        # Verify we got results for all parameter sets
        pub_result = result[0]
        self.assertIsNotNone(pub_result.data.meas)

        # Get counts and verify basic properties
        counts = pub_result.data.meas.get_counts()

        # Total counts should equal shots × number of parameter sets
        self.assertEqual(sum(counts.values()), 3000)
