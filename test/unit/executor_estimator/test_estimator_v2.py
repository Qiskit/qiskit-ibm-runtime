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

"""Unit tests for EstimatorV2 run method."""

from unittest.mock import MagicMock, patch

import numpy as np
from ddt import data, ddt, unpack
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.executor_estimator.estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2

from ...ibm_test_case import IBMTestCase
from ...utils import get_mocked_backend


@ddt
class TestEstimatorV2Run(IBMTestCase):
    """Tests for the EstimatorV2.run() method."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

        # Create a mock job to return from executor.run()
        self.mock_job = MagicMock(spec=RuntimeJobV2)
        self.mock_job.job_id.return_value = "test-job-id"

        # Patch Executor
        self.executor_patcher = patch("qiskit_ibm_runtime.executor_estimator.estimator.Executor")
        self.mock_executor_class = self.executor_patcher.start()

        # Create mock executor instance
        self.mock_executor_instance = MagicMock(spec=Executor)
        self.mock_executor_instance._backend = self.backend
        self.mock_executor_instance.run = MagicMock(return_value=self.mock_job)
        self.mock_executor_class.return_value = self.mock_executor_instance

    def tearDown(self):
        """Clean up patches."""
        self.executor_patcher.stop()

    def test_run_single_pub_no_parameters(self):
        """Test run with single pub without parameters."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable)], precision=0.03125)

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Verify the quantum program passed to executor
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertIsInstance(quantum_program, QuantumProgram)
        # precision=0.03125 -> shots = ceil(1/0.03125^2) = 1024
        self.assertEqual(quantum_program.shots, 1024)

        # Verify job was returned
        self.assertEqual(job, self.mock_job)

    def test_run_with_pub_level_precision(self):
        """Test that EstimatorPub.coerce is called with precision parameter."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable, None, 0.01)])

        self.mock_executor_instance.run.assert_called_once()
        # precision=0.01 -> shots = ceil(1/0.01^2) = 10000
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(quantum_program.shots, 10000)
        self.assertEqual(job, self.mock_job)

    def test_run_uses_default_precision_from_options(self):
        """Test that run uses default_precision from options when precision not specified."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.default_precision = 0.01
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)])

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Verify shots from precision were calculated
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(quantum_program.shots, 10000)

    def test_run_precision_parameter_overrides_options(self):
        """Test that precision parameter in run() overrides options.default_precision."""
        options = EstimatorOptions()
        options.default_precision = 0.022097  # sqrt(1/2048)

        estimator = EstimatorV2(mode=self.backend, options=options)
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)], precision=0.015625)

        # Verify precision parameter was used instead of options
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        # precision=0.015625 -> shots = ceil(1/0.015625^2) = 4096
        self.assertEqual(quantum_program.shots, 4096)

    def test_run_with_parametric_circuit(self):
        """Test run with parametric circuit."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        circuit.rx(theta, 0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        parameter_values = np.array([[0], [np.pi / 2], [np.pi]])

        job = estimator.run([(circuit, observable, parameter_values)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        self.assertEqual(job, self.mock_job)

    @data(True, False)
    def test_run_multiple_pubs(self, measure_mitigation):
        """Test run with multiple pubs."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience.measure_mitigation = measure_mitigation
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)

        circuit2 = QuantumCircuit(3)
        circuit2.h([0, 1, 2])

        observable1 = SparsePauliOp.from_list([("ZZ", 1)])
        observable2 = SparsePauliOp.from_list([("ZZZ", 1)])

        pubs = [(circuit1, observable1), (circuit2, observable2)]

        estimator.run(pubs, precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()

        # Verify multiple items in quantum program
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(len(quantum_program.items), 2 + measure_mitigation)

    def test_run_with_default_precision(self):
        """Test that run uses the default precision value from options."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience_level = 0
        # default_precision is 0.015625 by default

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)])

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Verify shots from default precision were calculated
        # precision=0.015625 -> shots = ceil(1/0.015625^2) = 4096
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(quantum_program.shots, 4096)

    def test_run_sets_executor_options(self):
        """Test that run sets executor options correctly."""
        options = EstimatorOptions()
        options.execution.init_qubits = True
        options.execution.rep_delay = 0.001
        options.max_execution_time = 300

        estimator = EstimatorV2(mode=self.backend, options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)], precision=0.03125)

        # Verify executor options were set
        self.assertIsNotNone(self.mock_executor_instance.options)
        self.assertTrue(self.mock_executor_instance.options.execution.init_qubits)
        self.assertEqual(self.mock_executor_instance.options.execution.rep_delay, 0.001)

    def test_run_adds_options_to_passthrough_data(self):
        """Test that run adds options metadata to quantum program passthrough data."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.dynamical_decoupling.enable = False
        options.resilience.measure_mitigation = True

        estimator = EstimatorV2(mode=self.backend, options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)], precision=0.03125)

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Get the quantum program passed to executor
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]

        # Verify passthrough data contains options
        self.assertIsNotNone(quantum_program.passthrough_data)
        self.assertIn("post_processor", quantum_program.passthrough_data)
        self.assertIn("options", quantum_program.passthrough_data["post_processor"])

        # Verify options content
        options_metadata = quantum_program.passthrough_data["post_processor"]["options"]
        self.assertEqual(options_metadata["twirling"]["enable_gates"], True)
        self.assertEqual(options_metadata["dynamical_decoupling"]["enable"], False)
        self.assertEqual(options_metadata["resilience"]["measure_mitigation"], True)

    def test_run_with_multiple_observables(self):
        """Test run with multiple observables in a single pub."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observables = [
            SparsePauliOp.from_list([("ZZ", 1)]),
            SparsePauliOp.from_list([("XX", 1)]),
            SparsePauliOp.from_list([("YY", 1)]),
        ]

        job = estimator.run([(circuit, observables)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        self.assertEqual(job, self.mock_job)

    def test_run_preserves_circuit_metadata(self):
        """Test that run preserves circuit metadata through the pipeline."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.metadata = {"test_key": "test_value"}

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        self.assertEqual(job, self.mock_job)

    @data((True, True), (True, False), (False, True), (False, False))
    @unpack
    @patch("qiskit_ibm_runtime.executor_estimator.estimator.apply_dynamical_decoupling")
    def test_run_applies_dynamical_decoupling_after_prepare(
        self, twirling_enabled, measure_mitigration, mock_apply_dd
    ):
        """Test apply_dynamical_decoupling is called when DD is enabled.

        Tests with twirling enabled and disabled (samplex item vs circuit item).
        """
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.dynamical_decoupling.enable = True
        estimator.options.twirling.enable_gates = twirling_enabled
        estimator.options.twirling.enable_measure = twirling_enabled
        estimator.options.resilience.measure_mitigation = measure_mitigration

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Mock to return the quantum program unchanged
        mock_apply_dd.side_effect = lambda backend, dd_options, quantum_program: quantum_program

        estimator.run([(circuit, observable), (circuit, observable)], precision=0.03125)

        # Verify apply_dynamical_decoupling was called once
        mock_apply_dd.assert_called_once()

    def test_run_rejects_dynamic_circuits_when_dynamical_decoupling_enabled(self):
        """Test DD rejects circuits with control flow."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.dynamical_decoupling.enable = True

        circuit = QuantumCircuit(2, 1)
        circuit.h(0)
        circuit.measure(0, 0)
        circuit.if_else((0, True), QuantumCircuit(2, 1), QuantumCircuit(2, 1), [0, 1], [0])

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with self.assertRaisesRegex(
            ValueError,
            "Dynamical decoupling is not compatible with dynamic circuits",
        ):
            estimator.run([(circuit, observable)], precision=0.03125)

    def test_run_incompatible_broadcast_shapes(self):
        """Test that incompatible parameter and observable shapes raise an error."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        circuit.rx(theta, 0)
        circuit.cx(0, 1)

        # Create observables with shape (3,)
        observables = [{"ZZ": 1}, {"XX": 1}, {"YY": 1}]

        # Create parameter values with shape (2,) - incompatible with (3,)
        parameter_values = np.array([[0], [np.pi / 2]])

        # Should raise ValueError when trying to run with incompatible shapes
        # The error will be raised during pub coercion in the run method
        with self.assertRaises(ValueError) as context:
            estimator.run([(circuit, observables, parameter_values)], precision=0.03125)

        # Verify the error message mentions broadcasting incompatibility
        self.assertIn("broadcastable", str(context.exception).lower())

    def test_run_mismatched_precision_raises_error(self):
        """Test that pubs with different precision values raise an error."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Create pubs with different precision values
        pub1 = EstimatorPub.coerce((circuit, observable), precision=0.01)
        pub2 = EstimatorPub.coerce((circuit, observable), precision=0.02)

        with self.assertRaises(IBMInputValueError) as context:
            estimator.run([pub1, pub2])
        self.assertIn("same precision", str(context.exception))

    def test_run_raises_error_when_no_pubs_provided(self):
        """Test that run raises IBMInputValueError when called with an empty pub list."""
        estimator = EstimatorV2(mode=self.backend)

        with self.assertRaisesRegex(IBMInputValueError, "No pubs provided"):
            estimator.run([])

        # Executor should never be reached
        self.mock_executor_instance.run.assert_not_called()

    def test_run_raises_error_when_pec_enabled_without_noise_model(self):
        """Test that run raises error when PEC is enabled but noise_model_mapping isn't."""
        estimator = EstimatorV2(mode=self.backend)

        # Enable PEC without providing noise model
        estimator.options.resilience.pec_mitigation = True
        estimator.options.resilience.noise_model_mapping = None

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with self.assertRaisesRegex(
            IBMInputValueError,
            "When PEC mitigation is enabled, you must provide a noise model",
        ):
            estimator.run([(circuit, observable)], precision=0.03125)

    @patch("qiskit_ibm_runtime.executor_estimator.estimator.prepare_pec")
    def test_run_dispatches_to_prepare_pec_when_pec_enabled(self, mock_prepare_pec):
        """Test that run calls prepare_pec when pec_mitigation is enabled."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience.pec_mitigation = True
        noise_model_mapping = {"layer_0": PauliLindbladMap.identity(num_qubits=2)}
        estimator.options.resilience.noise_model_mapping = noise_model_mapping

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Mock prepare_pec to return a valid QuantumProgram
        mock_qp = MagicMock(spec=QuantumProgram)
        mock_qp.shots = 1024
        mock_qp.passthrough_data = {"post_processor": {}}
        mock_qp.items = []
        mock_prepare_pec.return_value = mock_qp

        estimator.run([(circuit, observable)], precision=0.03125)

        mock_prepare_pec.assert_called_once()
        call_kwargs = mock_prepare_pec.call_args
        self.assertEqual(call_kwargs.kwargs["pec_options"], estimator.options.resilience.pec)
        self.assertEqual(call_kwargs.kwargs["noise_model_mapping"], noise_model_mapping)

    @patch("qiskit_ibm_runtime.executor_estimator.estimator.prepare_zne")
    def test_run_dispatches_to_prepare_zne_when_zne_enabled(self, mock_prepare_zne):
        """Test that run calls prepare_zne when zne_mitigation is enabled.

        with non-pea amplifier.
        """
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience.zne_mitigation = True

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Mock prepare_zne to return a valid QuantumProgram
        mock_qp = MagicMock(spec=QuantumProgram)
        mock_qp.shots = 1024
        mock_qp.passthrough_data = {"post_processor": {}}
        mock_qp.items = []
        mock_prepare_zne.return_value = mock_qp

        estimator.run([(circuit, observable)], precision=0.03125)

        mock_prepare_zne.assert_called_once()
        call_kwargs = mock_prepare_zne.call_args
        self.assertEqual(call_kwargs.kwargs["zne_options"], estimator.options.resilience.zne)

    def test_run_raises_error_when_pec_and_zne_both_enabled(self):
        """Test that run raises error when both pec_mitigation and zne_mitigation are enabled."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience.pec_mitigation = True
        estimator.options.resilience.zne_mitigation = True

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with self.assertRaisesRegex(
            IBMInputValueError,
            "PEC mitigation and ZNE mitigation are incompatible with one another",
        ):
            estimator.run([(circuit, observable)], precision=0.03125)

    @patch("qiskit_ibm_runtime.executor_estimator.estimator.prepare_pea")
    def test_run_dispatches_to_prepare_pea_when_pea_amplifier_selected(self, mock_prepare_pea):
        """Test that run calls prepare_pea when zne_mitigation is enabled with amplifier='pea'."""
        estimator = EstimatorV2(mode=self.backend)
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience.zne.amplifier = "pea"
        noise_model_mapping = {"layer_0": PauliLindbladMap.identity(num_qubits=2)}
        estimator.options.resilience.noise_model_mapping = noise_model_mapping

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Mock prepare_pea to return a valid QuantumProgram
        mock_qp = MagicMock(spec=QuantumProgram)
        mock_qp.shots = 1024
        mock_qp.passthrough_data = {"post_processor": {}}
        mock_qp.items = []
        mock_prepare_pea.return_value = mock_qp

        estimator.run([(circuit, observable)], precision=0.03125)

        mock_prepare_pea.assert_called_once()
        call_kwargs = mock_prepare_pea.call_args
        self.assertEqual(call_kwargs.kwargs["zne_options"], estimator.options.resilience.zne)
        self.assertEqual(call_kwargs.kwargs["noise_model_mapping"], noise_model_mapping)


class TestEstimatorV2SimulatorMode(IBMTestCase):
    """Tests for EstimatorV2 with local simulator backends."""

    def test_simulator_mode_skips_executor(self):
        """Test that a local backend (non-IBMBackend) skips the Executor."""
        backend = GenericBackendV2(num_qubits=5)
        estimator = EstimatorV2(mode=backend)

        self.assertIsNone(estimator._executor)

    def test_simulator_mode_returns_result(self):
        """Test that local mode returns expectation values close to the ideal.

        The Bell state (|00> + |11>)/sqrt(2) has <ZZ> = 1.0 exactly.
        With enough shots the noisy simulator should be within 0.1 of that.
        """
        backend = GenericBackendV2(num_qubits=5, seed=42)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator = EstimatorV2(mode=backend)
        estimator.options.default_shots = 10_000
        estimator.options.simulator.seed_simulator = 42
        result = estimator.run([(circuit, observable)]).result()

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0].data.evs, 1.0, delta=0.1)

    def test_simulator_mode_seed_is_deterministic(self):
        """Test that seed_simulator produces deterministic expectation values."""
        backend = GenericBackendV2(num_qubits=5)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator1 = EstimatorV2(mode=backend)
        estimator1.options.simulator.seed_simulator = 42
        estimator1.options.default_shots = 100
        result1 = estimator1.run([(circuit, observable)]).result()

        estimator2 = EstimatorV2(mode=backend)
        estimator2.options.simulator.seed_simulator = 42
        estimator2.options.default_shots = 100
        result2 = estimator2.run([(circuit, observable)]).result()

        np.testing.assert_array_equal(result1[0].data.evs, result2[0].data.evs)

    def test_simulator_mode_different_seeds_differ(self):
        """Test that different seeds produce different expectation values.

        Uses a single-qubit H gate whose <Z>=0 expectation value has shot-noise
        variance, so results differ between seeds with high probability.
        """
        backend = GenericBackendV2(num_qubits=5)

        # H|0> gives <Z>=0 with shot noise - results vary by seed
        circuit = QuantumCircuit(1)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("Z", 1)])

        estimator1 = EstimatorV2(mode=backend)
        estimator1.options.simulator.seed_simulator = 42
        estimator1.options.default_shots = 100
        result1 = estimator1.run([(circuit, observable)]).result()

        estimator2 = EstimatorV2(mode=backend)
        estimator2.options.simulator.seed_simulator = 99
        estimator2.options.default_shots = 100
        result2 = estimator2.run([(circuit, observable)]).result()

        self.assertFalse(np.array_equal(result1[0].data.evs, result2[0].data.evs))


@ddt
class TestFinalizeOptions(IBMTestCase):
    """Tests for ``finalize_options``."""

    def setUp(self):
        """Test level setup."""
        self.backend = get_mocked_backend()

    def test_resilience_level_0(self):
        """Tests for resilience level 0."""
        estimator = EstimatorV2(self.backend)
        estimator.options.resilience_level = 0

        finalized_options = estimator.finalize_options()
        self.assertFalse(finalized_options.twirling.enable_gates)
        self.assertFalse(finalized_options.twirling.enable_measure)
        self.assertFalse(finalized_options.resilience.measure_mitigation)
        self.assertFalse(finalized_options.resilience.zne_mitigation)

    def test_resilience_level_1(self):
        """Tests for resilience level 1."""
        estimator = EstimatorV2(self.backend)
        estimator.options.resilience_level = 1

        finalized_options = estimator.finalize_options()
        self.assertFalse(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
        self.assertTrue(finalized_options.resilience.measure_mitigation)
        self.assertFalse(finalized_options.resilience.zne_mitigation)

    def test_resilience_level_2(self):
        """Tests for resilience level 2."""
        estimator = EstimatorV2(self.backend)
        estimator.options.resilience_level = 2

        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
        self.assertTrue(finalized_options.resilience.measure_mitigation)
        self.assertTrue(finalized_options.resilience.zne_mitigation)

    @data(0, 1, 2)
    def test_set_values_are_preserved(self, resilience_level):
        """Test that when the user sets values, resilience level does not override them."""
        estimator = EstimatorV2(self.backend)
        estimator.options.twirling.enable_gates = False
        estimator.options.twirling.enable_measure = True
        estimator.options.resilience.measure_mitigation = False
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience_level = resilience_level

        finalized_options = estimator.finalize_options()
        self.assertFalse(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
        self.assertFalse(finalized_options.resilience.measure_mitigation)
        self.assertTrue(finalized_options.resilience.zne_mitigation)

    @data(0, 1, 2)
    def test_forced_values(self, resilience_level):
        """Test that finalize force-set certain values."""
        estimator = EstimatorV2(self.backend)
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.measure_mitigation = True
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_measure)

        estimator = EstimatorV2(self.backend)
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience.zne.amplifier = "pea"
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)

        estimator = EstimatorV2(self.backend)
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.pec_mitigation = True
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
