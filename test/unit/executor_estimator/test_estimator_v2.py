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
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.executor_estimator.estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.simulator import ExperimentalSimulatorOptions
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

        # Verify Executor was constructed with the correctly mapped executor options
        self.mock_executor_class.assert_called_once()
        executor_options = self.mock_executor_class.call_args[1]["options"]
        self.assertTrue(executor_options.execution.init_qubits)
        self.assertEqual(executor_options.execution.rep_delay, 0.001)
        self.assertEqual(executor_options.environment.max_execution_time, 300)

    def test_run_adds_options_to_passthrough_data(self):
        """Test that run adds options, shots and precision to passthrough data."""
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

        # Verify passthrough data contains inputs and calculated values
        self.assertIsNotNone(quantum_program.passthrough_data)
        self.assertIn("post_processor", quantum_program.passthrough_data)
        post_processor_data = quantum_program.passthrough_data["post_processor"]
        self.assertIn("options", post_processor_data)
        self.assertIn("shots", post_processor_data)
        self.assertIn("precision", post_processor_data)

        # Verify options content
        options_data = post_processor_data["options"]
        self.assertEqual(options_data["twirling"]["enable_gates"], True)
        self.assertEqual(options_data["dynamical_decoupling"]["enable"], False)
        self.assertEqual(options_data["resilience"]["measure_mitigation"], True)

    def test_run_passthrough_options_are_finalized_not_raw(self):
        """Test that run adds finalized options (not user options) to passthrough data."""
        # measure_mitigation=True force-resolves twirling.enable_measure -> True; the user
        # leaves enable_gates / enable_measure / zne_mitigation unset (raw value None).
        options = EstimatorOptions()
        options.resilience.measure_mitigation = True

        estimator = EstimatorV2(mode=self.backend, options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        quantum_program = self.mock_executor_instance.run.call_args[0][0]
        options_metadata = quantum_program.passthrough_data["post_processor"]["options"]

        # Unset fields must echo their RESOLVED default, never None.
        self.assertIsNotNone(options_metadata["twirling"]["enable_gates"])
        self.assertEqual(options_metadata["twirling"]["enable_measure"], True)
        self.assertEqual(options_metadata["twirling"]["enable_gates"], False)
        self.assertEqual(options_metadata["resilience"]["zne_mitigation"], False)

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


class TestEstimatorV2SimulatorMode(IBMTestCase):
    """Tests for EstimatorV2 with local simulator backends."""

    def test_simulator_mode_returns_result(self):
        """Test that local mode returns expectation values close to the ideal.

        The Bell state (|00> + |11>)/sqrt(2) has <ZZ> = 1.0 exactly.
        With enough shots the noisy simulator should be within 0.1 of that.
        """
        backend = GenericBackendV2(num_qubits=2, seed=42)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        transpiled = pm.run(circuit)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        simulator_options = ExperimentalSimulatorOptions(seed_simulator=42)

        estimator = EstimatorV2(
            mode=backend,
            options={"experimental": {"local_mode": True, "simulator_options": simulator_options}},
        )
        estimator.options.default_shots = 10_000
        result = estimator.run([(transpiled, observable)]).result()

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0].data.evs, 1.0, delta=0.1)

    def test_simulator_mode_seed_is_deterministic(self):
        """Test that seed_simulator produces deterministic expectation values."""
        backend = GenericBackendV2(num_qubits=2)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        transpiled = pm.run(circuit)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        simulator_options = ExperimentalSimulatorOptions(seed_simulator=42)

        estimator1 = EstimatorV2(
            mode=backend,
            options={"experimental": {"local_mode": True, "simulator_options": simulator_options}},
        )
        estimator1.options.default_shots = 100
        result1 = estimator1.run([(transpiled, observable)]).result()

        estimator2 = EstimatorV2(
            mode=backend,
            options={"experimental": {"local_mode": True, "simulator_options": simulator_options}},
        )
        estimator2.options.default_shots = 100
        result2 = estimator2.run([(transpiled, observable)]).result()

        np.testing.assert_array_equal(result1[0].data.evs, result2[0].data.evs)

    def test_simulator_mode_different_seeds_differ(self):
        """Test that different seeds produce different expectation values.

        Uses a single-qubit H gate whose <Z>=0 expectation value has shot-noise
        variance, so results differ between seeds with high probability.
        """
        backend = GenericBackendV2(num_qubits=2)

        # H|0> gives <Z>=0 with shot noise - results vary by seed
        circuit = QuantumCircuit(1)
        circuit.h(0)
        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        transpiled = pm.run(circuit)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        simulator_options = ExperimentalSimulatorOptions(seed_simulator=42)

        estimator1 = EstimatorV2(
            mode=backend,
            options={"experimental": {"local_mode": True, "simulator_options": simulator_options}},
        )
        estimator1.options.default_shots = 100
        result1 = estimator1.run([(transpiled, observable)]).result()

        simulator_options = ExperimentalSimulatorOptions(seed_simulator=99)

        estimator2 = EstimatorV2(
            mode=backend,
            options={"experimental": {"local_mode": True, "simulator_options": simulator_options}},
        )
        estimator2.options.default_shots = 100
        result2 = estimator2.run([(transpiled, observable)]).result()

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
