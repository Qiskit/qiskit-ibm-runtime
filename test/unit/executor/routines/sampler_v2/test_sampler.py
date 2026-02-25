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

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, BoxOp
from qiskit.primitives.containers.sampler_pub import SamplerPub

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerV2
from qiskit_ibm_runtime.executor.routines.sampler_v2.sampler import prepare
from qiskit_ibm_runtime.executor.routines.options import SamplerOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import CircuitItem
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem


def create_mock_backend():
    """Create a mock IBMBackend for testing."""
    backend = MagicMock(spec=IBMBackend)
    backend.name = "fake_backend"
    backend._instance = "ibm-q/open/main"

    # Mock the service
    service = MagicMock()
    backend.service = service

    return backend


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


class TestPrepare(unittest.TestCase):
    """Tests for prepare function."""

    def test_single_pub_no_parameters(self):
        """Test conversion of a single pub without parameters."""
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        program, executor_options = prepare([pub], options)

        self.assertIsInstance(program, QuantumProgram)
        self.assertEqual(program.shots, 1024)
        self.assertEqual(len(program.items), 1)
        self.assertIsInstance(program.items[0], CircuitItem)
        self.assertEqual(program.items[0].circuit, circuit)
        self.assertIsNotNone(executor_options)

    def test_single_pub_with_parameters(self):
        """Test conversion of a single pub with parameters."""
        theta = Parameter("θ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.measure_all()

        param_values = np.array([[0.1], [0.2], [0.3]])
        pub = SamplerPub.coerce((circuit, param_values), shots=2048)
        options = SamplerOptions()
        program, executor_options = prepare([pub], options)

        self.assertEqual(program.shots, 2048)
        self.assertEqual(len(program.items), 1)
        self.assertIsInstance(program.items[0], CircuitItem)
        np.testing.assert_array_equal(program.items[0].circuit_arguments, param_values)
        self.assertIsNotNone(executor_options)

    def test_multiple_pubs(self):
        """Test conversion of multiple pubs."""
        circuit1 = QuantumCircuit(2, 2)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(3, 3)
        circuit2.h([0, 1, 2])
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=1024),
            SamplerPub.coerce(circuit2, shots=1024),
        ]
        options = SamplerOptions()
        program, executor_options = prepare(pubs, options)

        self.assertEqual(program.shots, 1024)
        self.assertEqual(len(program.items), 2)
        self.assertEqual(program.items[0].circuit, circuit1)
        self.assertEqual(program.items[1].circuit, circuit2)
        self.assertIsNotNone(executor_options)

    def test_default_shots(self):
        """Test that default shots are used when not specified in pub."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots specified
        options = SamplerOptions()
        program, executor_options = prepare([pub], options, default_shots=4096)

        self.assertEqual(program.shots, 4096)
        self.assertIsNotNone(executor_options)

    def test_mismatched_shots_raises_error(self):
        """Test that mismatched shots across pubs raises an error."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(1, 1)
        circuit2.x(0)
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=1024),
            SamplerPub.coerce(circuit2, shots=2048),
        ]
        options = SamplerOptions()

        with self.assertRaises(IBMInputValueError) as context:
            prepare(pubs, options)

        self.assertIn("same number of shots", str(context.exception))

    def test_no_shots_specified_raises_error(self):
        """Test that missing shots raises an error."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots
        options = SamplerOptions()

        with self.assertRaises(IBMInputValueError) as context:
            prepare([pub], options, default_shots=None)

        self.assertIn("Shots must be specified", str(context.exception))

    def test_empty_pubs_raises_error(self):
        """Test that empty pubs list raises an error."""
        options = SamplerOptions()
        with self.assertRaises(IBMInputValueError) as context:
            prepare([], options)

        self.assertIn("At least one pub", str(context.exception))

    def test_pub_with_box_raises_error(self):
        """Test that a pub with a BoxOp raises an error."""


class TestPrepareOptionsHandling(unittest.TestCase):
    """Tests for options handling in prepare() function."""

    def test_prepare_returns_executor_options(self):
        """Test that prepare returns both QuantumProgram and ExecutorOptions."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()

        result = prepare([pub], options)

        # Should return a tuple
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        quantum_program, executor_options = result
        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertIsNotNone(executor_options)

    def test_prepare_maps_execution_options(self):
        """Test that prepare correctly maps execution options."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.execution.init_qubits = False
        options.execution.rep_delay = 0.0005

        _, executor_options = prepare([pub], options)

        self.assertEqual(executor_options.execution.init_qubits, False)
        self.assertEqual(executor_options.execution.rep_delay, 0.0005)

    def test_prepare_maps_environment_options(self):
        """Test that prepare correctly maps environment options."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.environment.log_level = "DEBUG"
        options.environment.job_tags = ["test", "prepare"]
        options.environment.private = True

        _, executor_options = prepare([pub], options)

        self.assertEqual(executor_options.environment.log_level, "DEBUG")
        self.assertEqual(executor_options.environment.job_tags, ["test", "prepare"])
        self.assertEqual(executor_options.environment.private, True)

    def test_prepare_maps_max_execution_time(self):
        """Test that prepare correctly maps max_execution_time."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.max_execution_time = 500

        _, executor_options = prepare([pub], options)

        self.assertEqual(executor_options.environment.max_execution_time, 500)

    def test_prepare_maps_experimental_image(self):
        """Test that prepare correctly maps experimental.image."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.experimental = {"image": "custom-runtime:v2"}

        _, executor_options = prepare([pub], options)

        self.assertEqual(executor_options.environment.image, "custom-runtime:v2")

    def test_prepare_extracts_meas_level_from_options(self):
        """Test that prepare extracts meas_level from options."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.execution.meas_type = "kerneled"

        quantum_program, _ = prepare([pub], options)

        self.assertEqual(quantum_program.meas_level, "kerneled")

    def test_prepare_uses_default_meas_level_when_unset(self):
        """Test that prepare uses 'classified' as default when meas_type is not set."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        # Don't set meas_type, it should default to Unset

        quantum_program, _ = prepare([pub], options)

        self.assertEqual(quantum_program.meas_level, "classified")

    def test_prepare_validates_dynamical_decoupling(self):
        """Test that prepare raises error for dynamical_decoupling."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.dynamical_decoupling.enable = True

        with self.assertRaises(NotImplementedError) as context:
            prepare([pub], options)

        self.assertIn("Dynamical decoupling", str(context.exception))

    def test_prepare_validates_experimental_options(self):
        """Test that prepare raises error for unsupported experimental options."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.experimental = {"unsupported_key": "value"}

        with self.assertRaises(NotImplementedError) as context:
            prepare([pub], options)

        self.assertIn("Experimental options", str(context.exception))

    def test_prepare_allows_experimental_image(self):
        """Test that prepare allows experimental.image."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.experimental = {"image": "allowed:v1"}

        # Should not raise
        _, executor_options = prepare([pub], options)
        self.assertEqual(executor_options.environment.image, "allowed:v1")

    def test_prepare_all_options_together(self):
        """Test that prepare correctly handles all supported options together."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=2048)
        options = SamplerOptions()
        options.execution.init_qubits = False
        options.execution.rep_delay = 0.0003
        options.execution.meas_type = "avg_kerneled"
        options.environment.log_level = "INFO"
        options.environment.job_tags = ["comprehensive", "test"]
        options.environment.private = True
        options.max_execution_time = 800
        options.experimental = {"image": "full-test:v1"}

        quantum_program, executor_options = prepare([pub], options)

        # Verify QuantumProgram
        self.assertEqual(quantum_program.shots, 2048)
        self.assertEqual(quantum_program.meas_level, "avg_kerneled")

        # Verify ExecutorOptions
        self.assertEqual(executor_options.execution.init_qubits, False)
        self.assertEqual(executor_options.execution.rep_delay, 0.0003)
        self.assertEqual(executor_options.environment.log_level, "INFO")
        self.assertEqual(executor_options.environment.job_tags, ["comprehensive", "test"])
        self.assertEqual(executor_options.environment.private, True)
        self.assertEqual(executor_options.environment.max_execution_time, 800)
        self.assertEqual(executor_options.environment.image, "full-test:v1")
        inner_circuit = QuantumCircuit(2)
        inner_circuit.h(0)

        circuit = QuantumCircuit(2, 2)
        circuit.append(BoxOp(inner_circuit), [0, 1])
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()

        with self.assertRaises(IBMInputValueError) as context:
            prepare([pub], options)
        self.assertIn("BoxOp", str(context.exception))


class TestPrepareTwirling(unittest.TestCase):
    """Unit tests for prepare() function with twirling enabled."""

    def test_prepare_creates_samplex_items(self):
        """Test that prepare() creates SamplexItem objects when twirling is enabled."""

        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        # Create pub and options
        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.twirling.enable_gates = True

        # Call prepare
        qp, _ = prepare([pub], options, default_shots=1024)

        # Verify SamplexItem was created
        self.assertEqual(len(qp.items), 1)
        self.assertIsInstance(qp.items[0], SamplexItem)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.build")
    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.generate_boxing_pass_manager")
    def test_prepare_calls_boxing_pm_with_correct_params(self, mock_boxing_pm, mock_build):
        """Test that prepare() calls boxing pass manager with correct twirling parameters."""
        # Setup mocks
        mock_pm_instance = MagicMock()
        mock_boxing_pm.return_value = mock_pm_instance
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()
        mock_pm_instance.run.return_value = circuit
        mock_build.return_value = (circuit, MagicMock())

        # Test different twirling configurations
        test_cases = [
            (True, False),  # Gates only
            (False, True),  # Measure only
            (True, True),  # Both enabled
        ]

        for enable_gates, enable_measure in test_cases:
            with self.subTest(enable_gates=enable_gates, enable_measure=enable_measure):
                mock_boxing_pm.reset_mock()

                pub = SamplerPub.coerce(circuit, shots=1024)
                options = SamplerOptions()
                options.twirling.enable_gates = enable_gates
                options.twirling.enable_measure = enable_measure

                prepare([pub], options, default_shots=1024)

                # Verify boxing PM was called with correct parameters
                mock_boxing_pm.assert_called_once()
                call_kwargs = mock_boxing_pm.call_args[1]
                self.assertEqual(call_kwargs["enable_gates"], bool(enable_gates))
                self.assertEqual(call_kwargs["enable_measures"], bool(enable_measure))

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.build")
    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.generate_boxing_pass_manager")
    def test_prepare_calls_samplomatic_build(self, mock_boxing_pm, mock_build):
        """Test that prepare() calls samplomatic.build with boxed circuit."""
        # Setup mocks
        mock_pm_instance = MagicMock()
        mock_boxing_pm.return_value = mock_pm_instance

        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        boxed_circuit = QuantumCircuit(1, 1)
        boxed_circuit.x(0)
        boxed_circuit.measure_all()
        mock_pm_instance.run.return_value = boxed_circuit

        mock_build.return_value = (boxed_circuit, MagicMock())

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.twirling.enable_gates = True

        prepare([pub], options, default_shots=1024)

        # Verify build was called with boxed circuit
        mock_build.assert_called_once_with(boxed_circuit)

    @patch("samplomatic.build")
    @patch("samplomatic.transpiler.generate_boxing_pass_manager")
    def test_prepare_calculates_shots_correctly(self, mock_boxing_pm, mock_build):
        """Test that prepare() calculates shots_per_randomization and num_randomizations correctly."""
        # Setup mocks
        mock_pm_instance = MagicMock()
        mock_boxing_pm.return_value = mock_pm_instance
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()
        mock_pm_instance.run.return_value = circuit
        mock_build.return_value = (circuit, MagicMock())

        test_cases = [
            # (pub_shots, num_rand, shots_per_rand, expected_qp_shots, expected_shape)
            (1024, "auto", "auto", 64, (16,)),  # Both auto
            (1024, "auto", 128, 128, (8,)),  # num_rand auto
            (1024, 10, "auto", 103, (10,)),  # shots_per_rand auto
            (1024, 20, 50, 50, (20,)),  # Both explicit
        ]

        for pub_shots, num_rand, shots_per_rand, expected_qp_shots, expected_shape in test_cases:
            with self.subTest(
                pub_shots=pub_shots, num_rand=num_rand, shots_per_rand=shots_per_rand
            ):
                pub = SamplerPub.coerce(circuit, shots=pub_shots)
                options = SamplerOptions()
                options.twirling.enable_gates = True
                options.twirling.num_randomizations = num_rand
                options.twirling.shots_per_randomization = shots_per_rand

                qp, _ = prepare([pub], options, default_shots=pub_shots)

                # Verify QuantumProgram shots (should be shots_per_randomization)
                self.assertEqual(qp.shots, expected_qp_shots)
                # Verify SamplexItem shape (should be num_randomizations)
                self.assertEqual(qp.items[0].shape, expected_shape)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.build")
    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.generate_boxing_pass_manager")
    def test_prepare_handles_strategy_option(self, mock_boxing_pm, mock_build):
        """Test that prepare() passes twirling strategy to boxing pass manager."""
        # Setup mocks
        mock_pm_instance = MagicMock()
        mock_boxing_pm.return_value = mock_pm_instance
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()
        mock_pm_instance.run.return_value = circuit
        mock_build.return_value = (circuit, MagicMock())

        strategies = ["active", "active-accum", "active-circuit", "all"]
        expected_strategies = ["active", "active_accum", "active_circuit", "all"]

        for strategy, expected in zip(strategies, expected_strategies):
            with self.subTest(strategy=strategy):
                mock_boxing_pm.reset_mock()

                pub = SamplerPub.coerce(circuit, shots=1024)
                options = SamplerOptions()
                options.twirling.enable_gates = True
                options.twirling.strategy = strategy

                prepare([pub], options, default_shots=1024)

                # Verify strategy was passed (with hyphen replaced by underscore)
                call_kwargs = mock_boxing_pm.call_args[1]
                self.assertEqual(call_kwargs["twirling_strategy"], expected)

    def test_prepare_handles_parametric_circuits(self):
        """Test that prepare() handles parametric circuits correctly."""
        theta = Parameter("θ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.measure_all()

        # Test with parameter values - use numpy array format
        param_values = np.array([[0.5], [1.0], [1.5]])
        pub = SamplerPub.coerce((circuit, param_values), shots=1024)
        options = SamplerOptions()
        options.twirling.enable_gates = True

        qp, _ = prepare([pub], options, default_shots=1024)

        # Verify SamplexItem was created with parameter values

        item = qp.items[0]
        self.assertIsInstance(item, SamplexItem)
        # samplex_arguments is a TensorInterface that acts like a dict
        self.assertTrue(np.array_equal(item.samplex_arguments["parameter_values"], param_values))
        # Shape should be (num_randomizations, num_parameter_sets) = (16, 3)
        self.assertEqual(item.shape, (16, 3))

    def test_prepare_handles_multiple_pubs(self):
        """Test that prepare() handles multiple pubs correctly."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(2, 2)
        circuit2.h([0, 1])
        circuit2.measure_all()

        pub1 = SamplerPub.coerce(circuit1, shots=1024)
        pub2 = SamplerPub.coerce(circuit2, shots=1024)
        options = SamplerOptions()
        options.twirling.enable_gates = True

        qp, _ = prepare([pub1, pub2], options, default_shots=1024)

        # Verify both pubs were processed
        self.assertEqual(len(qp.items), 2)

    def test_prepare_sets_passthrough_data(self):
        """Test that prepare() sets correct passthrough_data for post-processing."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.twirling.enable_gates = True

        qp, _ = prepare([pub], options, default_shots=1024)

        # Verify passthrough_data contains post-processor info
        self.assertIn("post_processor", qp.passthrough_data)
        self.assertEqual(qp.passthrough_data["post_processor"]["context"], "sampler_v2")
        self.assertEqual(qp.passthrough_data["post_processor"]["version"], "v1")
