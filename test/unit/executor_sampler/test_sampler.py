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

"""Tests for executor-based SamplerV2."""

from unittest import skipUnless
from unittest.mock import MagicMock, patch

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import BoxOp, Parameter
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.utils.optionals import HAS_AER

if HAS_AER:
    from qiskit_aer.noise import NoiseModel, depolarizing_error

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_sampler import SamplerV2

from ...ibm_test_case import IBMTestCase
from ...utils import get_mocked_backend


class TestSamplerV2SimpleCircuits(IBMTestCase):
    """Tests for SamplerV2 with simple (non-parametric) circuits."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_multiple_circuits_quantum_program_structure(self, mock_run):
        """Test QuantumProgram structure for multiple simple circuits."""
        mock_run.return_value = MagicMock()

        circuit1 = QuantumCircuit(2, 2)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(3, 3)
        circuit2.h([0, 1, 2])
        circuit2.measure_all()

        circuit3 = QuantumCircuit(1, 1)
        circuit3.x(0)
        circuit3.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit1, circuit2, circuit3], shots=2048)

        quantum_program = mock_run.call_args[0][0]

        # Verify QuantumProgram has all circuits
        self.assertEqual(quantum_program.shots, 2048)
        self.assertEqual(len(quantum_program.items), 3)

        # Verify each CircuitItem
        self.assertEqual(quantum_program.items[0].circuit, circuit1)

        self.assertEqual(quantum_program.items[1].circuit, circuit2)

        self.assertEqual(quantum_program.items[2].circuit, circuit3)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_default_shots(self, mock_run):
        """Test that default shots (4096) are used when not specified."""
        mock_run.return_value = MagicMock()

        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit])  # No shots specified

        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.shots, 4096)


class TestSamplerV2ParametricCircuits(IBMTestCase):
    """Tests for SamplerV2 with parametric circuits."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_single_parameter_multiple_values(self, mock_run):
        """Test parametric circuit with single parameter and multiple values."""
        mock_run.return_value = MagicMock()

        theta = Parameter("θ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.measure_all()

        param_values = [0.1, 0.2, 0.3, 0.4]
        sampler = SamplerV2(mode=self.backend)
        sampler.run([(circuit, param_values)], shots=2048)

        quantum_program = mock_run.call_args[0][0]
        item = quantum_program.items[0]

        # Verify circuit_arguments shape and values
        self.assertEqual(item.circuit_arguments.shape, (4, 1))
        expected = np.array([[0.1], [0.2], [0.3], [0.4]])
        np.testing.assert_array_almost_equal(item.circuit_arguments, expected)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_multiple_parameters_multiple_sets(self, mock_run):
        """Test parametric circuit with multiple parameters and multiple value sets."""
        mock_run.return_value = MagicMock()

        theta = Parameter("θ")
        phi = Parameter("φ")
        circuit = QuantumCircuit(2, 2)
        circuit.rx(theta, 0)
        circuit.rz(phi, 1)
        circuit.measure_all()

        param_values = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        sampler = SamplerV2(mode=self.backend)
        sampler.run([(circuit, param_values)], shots=512)

        quantum_program = mock_run.call_args[0][0]
        item = quantum_program.items[0]

        # Verify circuit_arguments shape and values
        self.assertEqual(item.circuit_arguments.shape, (3, 2))
        expected = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        np.testing.assert_array_almost_equal(item.circuit_arguments, expected)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_mixed_parametric_and_simple_circuits(self, mock_run):
        """Test mix of parametric and non-parametric circuits."""
        mock_run.return_value = MagicMock()

        # Simple circuit
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        # Parametric circuit
        theta = Parameter("θ")
        circuit2 = QuantumCircuit(1, 1)
        circuit2.rx(theta, 0)
        circuit2.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit1, (circuit2, [0.5, 1.0])], shots=1024)

        quantum_program = mock_run.call_args[0][0]

        # Verify both items
        self.assertEqual(len(quantum_program.items), 2)

        # First item: non-parametric
        item1 = quantum_program.items[0]
        self.assertEqual(item1.circuit, circuit1)
        self.assertEqual(item1.circuit_arguments.shape, (0,))

        # Second item: parametric
        item2 = quantum_program.items[1]
        self.assertEqual(item2.circuit, circuit2)
        self.assertEqual(item2.circuit_arguments.shape, (2, 1))
        np.testing.assert_array_almost_equal(item2.circuit_arguments, [[0.5], [1.0]])


class TestSamplerV2CircuitValidation(IBMTestCase):
    """Tests for circuit validation in SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_multiple_circuits_one_with_box_raises_error(self, mock_run):
        """Test that BoxOp in any circuit raises an error."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        inner_circuit = QuantumCircuit(2)
        inner_circuit.h(0)

        circuit2 = QuantumCircuit(2, 2)
        circuit2.append(BoxOp(inner_circuit), [0, 1])
        circuit2.measure_all()

        sampler = SamplerV2(mode=self.backend)

        with self.assertRaises(IBMInputValueError) as context:
            sampler.run([circuit1, circuit2], shots=1024)

        self.assertIn("BoxOp", str(context.exception))
        mock_run.assert_not_called()


class TestSamplerV2ShotsHandling(IBMTestCase):
    """Tests for shots handling in SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_default_shots_when_not_specified(self, mock_run):
        """Test that default shots (4096) are used when not specified."""
        mock_run.return_value = MagicMock()

        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit])

        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.shots, 4096)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_shots_consistency_across_pubs(self, mock_run):
        """Test that all pubs use the same shots value."""
        mock_run.return_value = MagicMock()

        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(2, 2)
        circuit2.h([0, 1])
        circuit2.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit1, circuit2], shots=2048)

        quantum_program = mock_run.call_args[0][0]

        # All items should use the same shots
        self.assertEqual(quantum_program.shots, 2048)


class TestSamplerV2QuantumProgramIntegrity(IBMTestCase):
    """Tests verifying the integrity of QuantumProgram objects created by SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_circuit_preservation(self, mock_run):
        """Test that circuits are preserved in QuantumProgram with empty metadata."""
        mock_run.return_value = MagicMock()

        # Create a circuit with specific structure
        circuit = QuantumCircuit(3, 3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.barrier()
        circuit.measure([0, 1, 2], [0, 1, 2])

        # add some metadata
        metadata = {"foo": True, "bar": np.int64(1)}
        circuit.metadata = metadata

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit], shots=1024)

        quantum_program = mock_run.call_args[0][0]
        item = quantum_program.items[0]

        # Verify circuit is equivalent and metadata is cleared on the copy
        self.assertEqual(item.circuit, circuit)
        self.assertEqual(item.circuit.metadata, {})

        # Verify that the original circuit is not mutated
        self.assertEqual(circuit.metadata, metadata)

        # Verify circuit structure is preserved
        self.assertEqual(item.circuit.num_qubits, 3)
        self.assertGreaterEqual(item.circuit.num_clbits, 3)
        # Circuit has h, cx, cx, barrier, and measure operations (measure_all may add multiple ops)
        self.assertGreaterEqual(len(item.circuit.data), 5)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_parameter_value_types(self, mock_run):
        """Test that parameter values are correctly converted to numpy arrays."""
        mock_run.return_value = MagicMock()

        theta = Parameter("θ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.measure_all()

        # Test with list input
        sampler = SamplerV2(mode=self.backend)
        sampler.run([(circuit, [0.1, 0.2, 0.3])], shots=1024)

        quantum_program = mock_run.call_args[0][0]
        item = quantum_program.items[0]

        # Verify circuit_arguments is a numpy array
        self.assertIsInstance(item.circuit_arguments, np.ndarray)
        self.assertEqual(item.circuit_arguments.dtype, np.float64)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_quantum_program_items_order(self, mock_run):
        """Test that QuantumProgram items maintain the order of input pubs."""
        mock_run.return_value = MagicMock()

        circuits = []
        for i in range(5):
            circuit = QuantumCircuit(1, 1, name=f"circuit_{i}")
            circuit.h(0)
            circuit.measure_all()
            circuits.append(circuit)

        sampler = SamplerV2(mode=self.backend)
        sampler.run(circuits, shots=1024)

        quantum_program = mock_run.call_args[0][0]

        # Verify order is preserved
        for i, item in enumerate(quantum_program.items):
            self.assertEqual(item.circuit.name, f"circuit_{i}")

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_circuit_item_shape_property(self, mock_run):
        """Test CircuitItem.shape property is correct for different parameter configurations."""
        mock_run.return_value = MagicMock()

        theta = Parameter("θ")
        phi = Parameter("φ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.rz(phi, 0)
        circuit.measure_all()

        # Test with 3 sets of 2 parameters
        param_values = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        sampler = SamplerV2(mode=self.backend)
        sampler.run([(circuit, param_values)], shots=1024)

        quantum_program = mock_run.call_args[0][0]
        item = quantum_program.items[0]

        # Shape should be (3,) - 3 parameter sets
        self.assertEqual(item.shape, (3,))
        self.assertEqual(item.size(), 3)


class TestSamplerV2DynamicalDecoupling(IBMTestCase):
    """Tests for SamplerV2 with dynamical decoupling enabled."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.apply_dynamical_decoupling")
    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_dd_pass_manager_called_when_enabled(self, mock_run, mock_apply_dd):
        """Test that apply_dynamical_decoupling is called when DD is enabled."""
        # Mock to return the quantum program unchanged
        mock_apply_dd.side_effect = lambda backend, dd_options, quantum_program: quantum_program
        mock_run.return_value = MagicMock()

        # Create a simple circuit
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        # Create sampler with DD enabled
        sampler = SamplerV2(mode=self.backend)
        sampler.options.dynamical_decoupling.enable = True
        sampler.options.dynamical_decoupling.sequence_type = "XX"

        # Run the sampler
        sampler.run([circuit], shots=1024)

        # Verify apply_dynamical_decoupling was called once
        mock_apply_dd.assert_called_once()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.apply_dynamical_decoupling")
    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_dd_pass_manager_not_called_when_disabled(self, mock_run, mock_apply_dd):
        """Test that apply_dynamical_decoupling is not called when DD is disabled."""
        mock_run.return_value = MagicMock()

        # Create a simple circuit
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        # Create sampler with DD disabled (default)
        sampler = SamplerV2(mode=self.backend)
        self.assertFalse(sampler.options.dynamical_decoupling.enable)

        # Run the sampler
        sampler.run([circuit], shots=1024)

        # Verify apply_dynamical_decoupling was NOT called
        mock_apply_dd.assert_not_called()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.apply_dynamical_decoupling")
    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
    def test_dd_with_twirling_enabled(self, mock_run, mock_apply_dd):
        """Test that apply_dynamical_decoupling is called when both DD and twirling are enabled."""
        # Mock to return the quantum program unchanged
        mock_apply_dd.side_effect = lambda backend, dd_options, quantum_program: quantum_program
        mock_run.return_value = MagicMock()

        # Create a simple circuit
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        # Create sampler with both DD and twirling enabled
        sampler = SamplerV2(mode=self.backend)
        sampler.options.dynamical_decoupling.enable = True
        sampler.options.dynamical_decoupling.sequence_type = "XpXm"
        sampler.options.twirling.enable_gates = True

        # Run the sampler
        sampler.run([circuit], shots=1024)

        # Verify apply_dynamical_decoupling was called once
        mock_apply_dd.assert_called_once()

    def test_dd_raises_error_with_multiple_circuits_one_has_control_flow(self):
        """Test that DD raises ValueError when one of multiple circuits has control flow."""
        # Create a simple circuit without control flow
        circuit1 = QuantumCircuit(2, 2)
        circuit1.h(0)
        circuit1.cx(0, 1)
        circuit1.measure_all()

        # Create a circuit with control flow
        circuit2 = QuantumCircuit(2, 2)
        circuit2.h(0)
        circuit2.measure(0, 0)
        with circuit2.if_test((0, 1)):
            circuit2.x(1)
        circuit2.measure(1, 1)

        # Create sampler with DD enabled
        sampler = SamplerV2(mode=self.backend)
        sampler.options.dynamical_decoupling.enable = True

        # Verify that running with DD enabled raises ValueError
        with self.assertRaises(ValueError) as context:
            sampler.run([circuit1, circuit2], shots=1024)

        # Check the error message
        self.assertIn(
            "Dynamical decoupling is not compatible with dynamic circuits", str(context.exception)
        )


class TestSamplerV2SimulatorMode(IBMTestCase):
    """Tests for SamplerV2 with simulator backends (local mode)."""

    def test_simulator_mode_uses_backend_sampler(self):
        """Test that simulator mode uses BackendSamplerV2 instead of Executor."""
        backend = GenericBackendV2(num_qubits=5)

        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        sampler = SamplerV2(mode=backend)

        # Verify executor is not created for simulator
        self.assertIsNone(sampler._executor)

        # Run should work and return results
        job = sampler.run([circuit], shots=100)
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

        # First sampler with seed
        sampler1 = SamplerV2(mode=backend)
        sampler1.options.simulator.seed_simulator = 42
        sampler1.options.default_shots = 200

        job1 = sampler1.run([circuit])
        result1 = job1.result()
        counts1 = result1[0].data.meas.get_counts()

        # Second sampler with same seed
        sampler2 = SamplerV2(mode=backend)
        sampler2.options.simulator.seed_simulator = 42
        sampler2.options.default_shots = 200

        job2 = sampler2.run([circuit])
        result2 = job2.result()
        counts2 = result2[0].data.meas.get_counts()

        # Results should be identical with same seed
        self.assertEqual(counts1, counts2)

        # Third sampler with different seed should give different results
        sampler3 = SamplerV2(mode=backend)
        sampler3.options.simulator.seed_simulator = 123
        sampler3.options.default_shots = 200

        job3 = sampler3.run([circuit])
        result3 = job3.result()
        counts3 = result3[0].data.meas.get_counts()

        # Results should be different with different seed
        self.assertNotEqual(counts1, counts3)

    @skipUnless(condition=HAS_AER, reason="qiskit-aer is required to run this test")
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

        # Parameter sweep with multiple parameter value sets
        param_values = [
            [0.0, 0.0],  # First parameter set
            [np.pi / 2, np.pi / 4],  # Second parameter set
            [np.pi, np.pi / 2],  # Third parameter set
        ]

        # Create sampler with all simulator options
        sampler = SamplerV2(mode=backend)

        # Set noise model (simple depolarizing noise)

        noise_model = NoiseModel()
        # Add depolarizing error to single-qubit gates
        error_1q = depolarizing_error(0.001, 1)
        noise_model.add_all_qubit_quantum_error(error_1q, ["h", "rx", "ry"])
        # Add depolarizing error to two-qubit gates
        error_2q = depolarizing_error(0.01, 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ["cx"])

        sampler.options.simulator.noise_model = noise_model

        # Set coupling map (linear topology for 3 qubits)
        sampler.options.simulator.coupling_map = [[0, 1], [1, 0], [1, 2], [2, 1]]

        # Set basis gates
        sampler.options.simulator.basis_gates = ["h", "rx", "ry", "cx", "id"]

        # Set seed for reproducibility
        sampler.options.simulator.seed_simulator = 42

        # Run with parameter sweep
        job = sampler.run([(circuit, param_values)], shots=1000)
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
