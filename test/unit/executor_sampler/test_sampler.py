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
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.circuit import BoxOp, Parameter
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit_aer.noise import NoiseModel, depolarizing_error

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_sampler import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.options_models import SamplerOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import CircuitItem, SamplexItem


def create_mock_backend():
    """Create a mock IBMBackend for testing."""
    backend = MagicMock(spec=IBMBackend)
    backend.name = "fake_backend"
    backend._instance = "ibm-q/open/main"

    # Mock the service
    service = MagicMock()
    backend.service = service
    backend.target = FakeManilaV2().target

    return backend


def create_sampler_for_prepare_tests(options=None):
    """Create a SamplerV2 instance for testing the prepare method.

    Args:
        backend: Backend to use. If None, uses a mock backend.
        options: SamplerOptions to use. If None, uses default SamplerOptions().

    Returns:
        SamplerV2 instance configured for testing.
    """
    backend = create_mock_backend()
    if options is None:
        options = SamplerOptions()

    sampler = SamplerV2(mode=backend, options=options)
    return sampler


class TestSamplerV2SimpleCircuits(unittest.TestCase):
    """Tests for SamplerV2 with simple (non-parametric) circuits."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

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


class TestSamplerV2ParametricCircuits(unittest.TestCase):
    """Tests for SamplerV2 with parametric circuits."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

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


class TestSamplerV2CircuitValidation(unittest.TestCase):
    """Tests for circuit validation in SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

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


class TestSamplerV2ShotsHandling(unittest.TestCase):
    """Tests for shots handling in SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

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


class TestSamplerV2QuantumProgramIntegrity(unittest.TestCase):
    """Tests verifying the integrity of QuantumProgram objects created by SamplerV2."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.Executor.run")
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


class TestPrepare(unittest.TestCase):
    """Tests for prepare method."""

    def test_multiple_pubs(self):
        """Test conversion of multiple pubs, including parametric circuits."""
        # Non-parametric circuit
        circuit1 = QuantumCircuit(2, 2)
        circuit1.h(0)
        circuit1.measure_all()

        # Parametric circuit
        theta = Parameter("θ")
        circuit2 = QuantumCircuit(1, 1)
        circuit2.rx(theta, 0)
        circuit2.measure_all()
        param_values = np.array([[0.1], [0.2], [0.3]])

        # Another non-parametric circuit
        circuit3 = QuantumCircuit(3, 3)
        circuit3.h([0, 1, 2])
        circuit3.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=1024),
            SamplerPub.coerce((circuit2, param_values), shots=1024),
            SamplerPub.coerce(circuit3, shots=1024),
        ]
        sampler = create_sampler_for_prepare_tests()
        program, executor_options = sampler.prepare(pubs)

        self.assertEqual(program.shots, 1024)
        self.assertEqual(len(program.items), 3)

        # Verify non-parametric circuit
        self.assertEqual(program.items[0].circuit, circuit1)
        self.assertIsInstance(program.items[0], CircuitItem)

        # Verify parametric circuit
        self.assertEqual(program.items[1].circuit, circuit2)
        self.assertIsInstance(program.items[1], CircuitItem)
        np.testing.assert_array_equal(program.items[1].circuit_arguments, param_values)

        # Verify another non-parametric circuit
        self.assertEqual(program.items[2].circuit, circuit3)

        self.assertIsNotNone(executor_options)

    def test_default_shots(self):
        """Test that default shots are used when not specified in pub."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots specified
        sampler = create_sampler_for_prepare_tests()
        program, executor_options = sampler.prepare([pub], default_shots=4096)

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
        sampler = create_sampler_for_prepare_tests()

        with self.assertRaises(IBMInputValueError) as context:
            sampler.prepare(pubs)

        self.assertIn("same number of shots", str(context.exception))

    def test_no_shots_specified_raises_error(self):
        """Test that missing shots raises an error."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots
        sampler = create_sampler_for_prepare_tests()

        with self.assertRaises(IBMInputValueError) as context:
            sampler.prepare([pub], default_shots=None)

        self.assertIn("Shots must be specified", str(context.exception))

    def test_pub_with_box_raises_error(self):
        """Test that a pub with a BoxOp raises an error."""
        circuit = QuantumCircuit(2, 2)
        with circuit.box():
            circuit.x(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        sampler = create_sampler_for_prepare_tests()

        with self.assertRaises(IBMInputValueError) as context:
            sampler.prepare([pub])

        self.assertIn("BoxOp", str(context.exception))
        self.assertIn("not supported", str(context.exception))


class TestPrepareOptionsHandling(unittest.TestCase):
    """Tests for options handling in prepare() method."""

    def test_prepare_returns_executor_options(self):
        """Test that prepare returns both QuantumProgram and ExecutorOptions."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        sampler = create_sampler_for_prepare_tests()

        result = sampler.prepare([pub])

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
        sampler = create_sampler_for_prepare_tests(options=options)

        _, executor_options = sampler.prepare([pub])

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
        sampler = create_sampler_for_prepare_tests(options=options)

        _, executor_options = sampler.prepare([pub])

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
        sampler = create_sampler_for_prepare_tests(options=options)

        _, executor_options = sampler.prepare([pub])

        self.assertEqual(executor_options.environment.max_execution_time, 500)

    def test_prepare_maps_experimental_image(self):
        """Test that prepare correctly maps experimental.image."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.experimental = {"image": "custom-runtime:v2"}
        sampler = create_sampler_for_prepare_tests(options=options)

        _, executor_options = sampler.prepare([pub])

        self.assertEqual(executor_options.environment.image, "custom-runtime:v2")

    def test_prepare_extracts_meas_level_from_options(self):
        """Test that prepare extracts meas_level from options."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.execution.meas_type = "kerneled"
        sampler = create_sampler_for_prepare_tests(options=options)

        quantum_program, _ = sampler.prepare([pub])

        self.assertEqual(quantum_program.meas_level, "kerneled")

    def test_prepare_uses_default_meas_level_when_unset(self):
        """Test that prepare uses 'classified' as default when meas_type is not set."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        sampler = create_sampler_for_prepare_tests()
        # Don't set meas_type, it should default to Unset

        quantum_program, _ = sampler.prepare([pub])

        self.assertEqual(quantum_program.meas_level, "classified")

    def test_prepare_allows_experimental_image(self):
        """Test that prepare allows experimental.image."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.experimental = {"image": "allowed:v1"}
        sampler = create_sampler_for_prepare_tests(options=options)

        # Should not raise
        _, executor_options = sampler.prepare([pub])
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
        sampler = create_sampler_for_prepare_tests(options=options)

        quantum_program, executor_options = sampler.prepare([pub])

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


class TestPrepareTwirling(unittest.TestCase):
    """Unit tests for prepare() method with twirling enabled."""

    def test_prepare_creates_samplex_items(self):
        """Test that prepare() creates SamplexItem objects when twirling is enabled."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        # Create pub and options
        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.twirling.enable_gates = True
        sampler = create_sampler_for_prepare_tests(options=options)

        # Call prepare
        qp, _ = sampler.prepare([pub], default_shots=1024)

        # Verify SamplexItem was created
        self.assertEqual(len(qp.items), 1)
        self.assertIsInstance(qp.items[0], SamplexItem)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.build")
    @patch("qiskit_ibm_runtime.executor_sampler.sampler.generate_boxing_pass_manager")
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
                sampler = create_sampler_for_prepare_tests(options=options)

                sampler.prepare([pub], default_shots=1024)

                # Verify boxing PM was called with correct parameters
                mock_boxing_pm.assert_called_once()
                call_kwargs = mock_boxing_pm.call_args[1]
                self.assertEqual(call_kwargs["enable_gates"], bool(enable_gates))
                self.assertEqual(call_kwargs["enable_measures"], bool(enable_measure))

    def test_prepare_rejects_measurement_twirling_with_kerneled(self):
        """prepare() rejects measurement twirling combined with a kerneled meas_type.

        Measurement twirling flips bits and XOR-corrects them in post-processing, which is only
        defined for classified bit results -- not the complex IQ data of kerneled/avg_kerneled.
        """
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()
        pub = SamplerPub.coerce(circuit, shots=1024)

        # enable_measure + kerneled / avg_kerneled is rejected up front.
        for meas_type in ("kerneled", "avg_kerneled"):
            with self.subTest(meas_type=meas_type):
                options = SamplerOptions()
                options.twirling.enable_measure = True
                options.execution.meas_type = meas_type
                sampler = create_sampler_for_prepare_tests(options=options)
                with self.assertRaisesRegex(IBMInputValueError, "not compatible"):
                    sampler.prepare([pub], default_shots=1024)

        # The same kerneled meas_type is allowed when measurement twirling is off.
        options = SamplerOptions()
        options.twirling.enable_measure = False
        options.execution.meas_type = "kerneled"
        sampler = create_sampler_for_prepare_tests(options=options)
        sampler.prepare([pub], default_shots=1024)  # must not raise

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.build")
    @patch("qiskit_ibm_runtime.executor_sampler.sampler.generate_boxing_pass_manager")
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
        sampler = create_sampler_for_prepare_tests(options=options)

        sampler.prepare([pub], default_shots=1024)

        # Verify build was called with boxed circuit
        mock_build.assert_called_once_with(boxed_circuit)

    @patch("samplomatic.build")
    @patch("samplomatic.transpiler.generate_boxing_pass_manager")
    def test_prepare_calculates_shots_correctly(self, mock_boxing_pm, mock_build):
        """Test prepare() calculates shots_per_randomization and num_randomizations correctly."""
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
                sampler = create_sampler_for_prepare_tests(options=options)

                qp, _ = sampler.prepare([pub], default_shots=pub_shots)

                # Verify QuantumProgram shots (should be shots_per_randomization)
                self.assertEqual(qp.shots, expected_qp_shots)
                # Verify SamplexItem shape (should be num_randomizations)
                self.assertEqual(qp.items[0].shape, expected_shape)

    @patch("qiskit_ibm_runtime.executor_sampler.sampler.build")
    @patch("qiskit_ibm_runtime.executor_sampler.sampler.generate_boxing_pass_manager")
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
                options.twirling.strategy = strategy  # type: ignore[assignment]
                sampler = create_sampler_for_prepare_tests(options=options)

                sampler.prepare([pub], default_shots=1024)

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
        sampler = create_sampler_for_prepare_tests(options=options)

        qp, _ = sampler.prepare([pub], default_shots=1024)

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
        sampler = create_sampler_for_prepare_tests(options=options)

        qp, _ = sampler.prepare([pub1, pub2], default_shots=1024)

        # Verify both pubs were processed
        self.assertEqual(len(qp.items), 2)


@ddt
class TestPreparePassthroughData(unittest.TestCase):
    """Unit tests for prepare() method, checking passthrough_data."""

    @data(True, False)
    def test_prepare_sets_passthrough_data(self, enable_gates):
        """Test that prepare() sets correct passthrough_data for post-processing."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.twirling.enable_gates = enable_gates
        sampler = create_sampler_for_prepare_tests(options=options)

        qp, _ = sampler.prepare([pub], default_shots=1024)

        # Verify passthrough_data contains post-processor info
        self.assertIn("post_processor", qp.passthrough_data)
        self.assertEqual(qp._semantic_role, "sampler_v2")
        self.assertEqual(qp.passthrough_data["post_processor"]["version"], "v0.1")
        self.assertEqual(qp.passthrough_data["post_processor"]["meas_type"], "classified")
        self.assertEqual(qp.passthrough_data["post_processor"]["twirling"], enable_gates)

    def test_prepare_includes_options_in_passthrough_data(self):
        """Test that prepare() includes options dictionary in passthrough_data."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions()
        options.default_shots = 2048
        options.twirling.enable_gates = True
        options.twirling.strategy = "all"  # type: ignore[assignment]
        options.execution.meas_type = "kerneled"
        options.environment.log_level = "DEBUG"
        sampler = create_sampler_for_prepare_tests(options=options)

        qp, _ = sampler.prepare([pub], default_shots=1024)

        # Verify options dictionary is present in passthrough_data
        self.assertIn("post_processor", qp.passthrough_data)
        self.assertIn("post_processor", qp.passthrough_data)
        self.assertEqual(qp._semantic_role, "sampler_v2")
        self.assertEqual(qp.passthrough_data["post_processor"]["version"], "v0.1")
        self.assertEqual(qp.passthrough_data["post_processor"]["twirling"], True)
        self.assertEqual(qp.passthrough_data["post_processor"]["meas_type"], "kerneled")


class TestSamplerV2DynamicalDecoupling(unittest.TestCase):
    """Tests for SamplerV2 with dynamical decoupling enabled."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()

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


class TestSamplerV2SimulatorMode(unittest.TestCase):
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
