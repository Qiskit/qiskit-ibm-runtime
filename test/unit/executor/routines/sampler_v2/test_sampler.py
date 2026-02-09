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

"""Tests for executor-based SamplerV2."""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, BoxOp

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerV2
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import CircuitItem
from qiskit_ibm_runtime.ibm_backend import IBMBackend


def create_mock_backend():
    """Create a mock IBMBackend for testing."""
    backend = MagicMock(spec=IBMBackend)
    backend.name = "fake_backend"
    backend._instance = "ibm-q/open/main"

    # Mock the service
    service = MagicMock()
    backend.service = service

    return backend


class TestSamplerV2Initialization(unittest.TestCase):
    """Tests for SamplerV2 initialization and basic properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    def test_version(self):
        """Test that version is set correctly."""
        sampler = SamplerV2(mode=self.backend)
        self.assertEqual(sampler.version, 2)


class TestSamplerV2SimpleCircuits(unittest.TestCase):
    """Tests for SamplerV2 with simple (non-parametric) circuits."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_single_circuit_quantum_program_structure(self, mock_run):
        """Test QuantumProgram structure for a single simple circuit."""
        mock_run.return_value = MagicMock()

        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit], shots=1024)

        # Verify Executor run was called once
        self.assertEqual(mock_run.call_count, 1)

        # Extract the QuantumProgram
        quantum_program = mock_run.call_args[0][0]

        # Verify QuantumProgram structure
        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, 1024)
        self.assertEqual(len(quantum_program.items), 1)

        # Verify CircuitItem
        item = quantum_program.items[0]
        self.assertIsInstance(item, CircuitItem)
        self.assertEqual(item.circuit, circuit)
        self.assertEqual(item.circuit.num_qubits, 2)
        self.assertEqual(item.circuit.num_clbits, 4)

        # Verify circuit_arguments for non-parametric circuit
        self.assertIsNotNone(item.circuit_arguments)
        self.assertEqual(item.circuit_arguments.shape, (0,))

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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


class TestSamplerV2ParametricCircuits(unittest.TestCase):
    """Tests for SamplerV2 with parametric circuits."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_single_parameter_single_value(self, mock_run):
        """Test parametric circuit with single parameter and single value."""
        mock_run.return_value = MagicMock()

        theta = Parameter("θ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([(circuit, [0.5])], shots=1024)

        quantum_program = mock_run.call_args[0][0]

        # Verify QuantumProgram
        self.assertEqual(quantum_program.shots, 1024)
        self.assertEqual(len(quantum_program.items), 1)

        # Verify CircuitItem with parameters
        item = quantum_program.items[0]
        self.assertIsInstance(item, CircuitItem)
        self.assertEqual(item.circuit, circuit)
        self.assertEqual(item.circuit.num_parameters, 1)

        # Verify circuit_arguments shape and values
        self.assertIsNotNone(item.circuit_arguments)
        self.assertEqual(item.circuit_arguments.shape, (1,))
        np.testing.assert_array_almost_equal(item.circuit_arguments, [0.5])

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_multiple_parameters_single_set(self, mock_run):
        """Test parametric circuit with multiple parameters and single value set."""
        mock_run.return_value = MagicMock()

        theta = Parameter("θ")
        phi = Parameter("φ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.rz(phi, 0)
        circuit.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([(circuit, [[0.5, 1.2]])], shots=1024)

        quantum_program = mock_run.call_args[0][0]
        item = quantum_program.items[0]

        # Verify circuit has 2 parameters
        self.assertEqual(item.circuit.num_parameters, 2)

        # Verify circuit_arguments shape and values
        self.assertEqual(item.circuit_arguments.shape, (1, 2))
        np.testing.assert_array_almost_equal(item.circuit_arguments, [[0.5, 1.2]])

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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


class TestSamplerV2CircuitValidation(unittest.TestCase):
    """Tests for circuit validation in SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_circuit_with_box_raises_error(self, mock_run):
        """Test that running a circuit with BoxOp raises an error."""
        inner_circuit = QuantumCircuit(2)
        inner_circuit.h(0)
        inner_circuit.cx(0, 1)

        circuit = QuantumCircuit(2, 2)
        circuit.append(BoxOp(inner_circuit), [0, 1])
        circuit.measure_all()

        sampler = SamplerV2(mode=self.backend)

        with self.assertRaises(IBMInputValueError) as context:
            sampler.run([circuit], shots=1024)

        self.assertIn("BoxOp", str(context.exception))
        self.assertIn("not supported", str(context.exception))

        # Verify executor.run was never called
        mock_run.assert_not_called()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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


class TestSamplerV2ShotsHandling(unittest.TestCase):
    """Tests for shots handling in SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_explicit_shots_in_run(self, mock_run):
        """Test that explicit shots in run() are used."""
        mock_run.return_value = MagicMock()

        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit], shots=8192)

        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.shots, 8192)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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


class TestSamplerV2ErrorConditions(unittest.TestCase):
    """Tests for error conditions in SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_empty_pubs_raises_error(self, mock_run):
        """Test that empty pubs list raises an error."""
        sampler = SamplerV2(mode=self.backend)

        with self.assertRaises(IBMInputValueError) as context:
            sampler.run([], shots=1024)

        self.assertIn("At least one pub", str(context.exception))
        mock_run.assert_not_called()


class TestSamplerV2QuantumProgramIntegrity(unittest.TestCase):
    """Tests verifying the integrity of QuantumProgram objects created by SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_circuit_preservation(self, mock_run):
        """Test that circuits are preserved exactly in QuantumProgram."""
        mock_run.return_value = MagicMock()

        # Create a circuit with specific structure
        circuit = QuantumCircuit(3, 3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.barrier()
        circuit.measure([0, 1, 2], [0, 1, 2])

        sampler = SamplerV2(mode=self.backend)
        sampler.run([circuit], shots=1024)

        quantum_program = mock_run.call_args[0][0]
        item = quantum_program.items[0]

        # Verify circuit is the same object
        self.assertIs(item.circuit, circuit)

        # Verify circuit structure is preserved
        self.assertEqual(item.circuit.num_qubits, 3)
        self.assertGreaterEqual(item.circuit.num_clbits, 3)
        # Circuit has h, cx, cx, barrier, and measure operations (measure_all may add multiple ops)
        self.assertGreaterEqual(len(item.circuit.data), 5)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
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

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_circuit_item_shape_property(self, mock_run):
        """Test that CircuitItem.shape property is correct for different parameter configurations."""
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
