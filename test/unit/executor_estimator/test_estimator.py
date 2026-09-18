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

"""Unit tests for Estimator run method."""

import warnings
from unittest.mock import MagicMock, patch

import numpy as np
from ddt import data, ddt
from pydantic import ValidationError
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.executor_estimator.estimator import Estimator
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.environment import EnvironmentOptions
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.execution import ExecutionOptions
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2
from qiskit_ibm_runtime.session import Session

from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...registries import OneInstanceDryRunRegistry
from ...utils import get_mocked_backend


class TestEstimatorUsingOptions(IBMTestCase):
    """Tests option setting on the ``Estimator`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        estimator = Estimator(mode=FakeBrisbane())
        self.assertIsInstance(estimator.options, EstimatorOptions)
        self.assertEqual(estimator.options, EstimatorOptions())

    def test_options_from_instance(self):
        """Test constructing with an EstimatorOptions instance."""
        opts = EstimatorOptions(execution=ExecutionOptions(init_qubits=False))
        estimator = Estimator(mode=FakeBrisbane(), options=opts)
        self.assertIs(estimator.options, opts)
        self.assertFalse(estimator.options.execution.init_qubits)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        estimator = Estimator(mode=FakeBrisbane(), options=opts_dict)
        self.assertFalse(estimator.options.execution.init_qubits)
        self.assertEqual(estimator.options.execution.rep_delay, 0.5)
        self.assertEqual(estimator.options.environment.log_level, "DEBUG")
        self.assertEqual(estimator.options.environment.job_tags, ["tag1"])

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        estimator = Estimator(mode=FakeBrisbane(), options={"execution": {"init_qubits": False}})
        self.assertFalse(estimator.options.execution.init_qubits)
        self.assertIsNone(estimator.options.execution.rep_delay)
        self.assertEqual(estimator.options.environment, EnvironmentOptions())

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected EstimatorOptions or dict"):
            Estimator(mode=FakeBrisbane(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an EstimatorOptions instance."""
        estimator = Estimator(mode=FakeBrisbane())
        new_opts = EstimatorOptions(execution=ExecutionOptions(init_qubits=False))
        estimator.options = new_opts
        self.assertIs(estimator.options, new_opts)

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        estimator = Estimator(mode=FakeBrisbane())
        estimator.options = {"execution": {"init_qubits": False}}
        self.assertIsInstance(estimator.options, EstimatorOptions)
        self.assertFalse(estimator.options.execution.init_qubits)

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        estimator = Estimator(mode=FakeBrisbane())
        with self.assertRaisesRegex(TypeError, "Expected EstimatorOptions or dict"):
            estimator.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        estimator = Estimator(mode=FakeBrisbane(), options={"environment": {"log_level": "DEBUG"}})
        estimator.options = {"execution": {"init_qubits": False}}
        # environment should be back to defaults since we replaced, not updated
        self.assertEqual(estimator.options.environment.log_level, "WARNING")
        self.assertFalse(estimator.options.execution.init_qubits)

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        estimator = Estimator(mode=FakeBrisbane())
        self.assertEqual(estimator.options.experimental, {})

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        estimator = Estimator(mode=FakeBrisbane(), options=opts_dict)
        self.assertEqual(estimator.options.experimental, {"foo": "bar", "baz": 123})

    def test_experimental_options_from_instance(self):
        """Test constructing with an EstimatorOptions instance with experimental options."""
        opts = EstimatorOptions(experimental={"custom_key": "custom_value"})
        estimator = Estimator(mode=FakeBrisbane(), options=opts)
        self.assertEqual(estimator.options.experimental, {"custom_key": "custom_value"})

    def test_experimental_options_setter(self):
        """Test setting experimental options via the setter."""
        estimator = Estimator(mode=FakeBrisbane())
        estimator.options = {"experimental": {"test": "value"}}
        self.assertEqual(estimator.options.experimental, {"test": "value"})

    def test_validation_on_mutation(self):
        """Test validation errors are raised on mutation, not just construction."""
        options = ExecutionOptions(init_qubits=False)
        with self.assertRaises(ValidationError):
            options.init_qubits = [0, 1]

    def test_extra_variables_are_forbidden(self):
        """Test that we can not set variables undefined by the model."""
        options = ExecutionOptions()
        with self.assertRaises(ValidationError):
            options.not_a_variable = 0


@ddt
class TestEstimatorRun(IBMTestCase):
    """Tests for the Estimator.run() method."""

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
        estimator = Estimator(mode=self.backend)
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

        # Verify that information needed for post-processing dispatch were attached
        self.assertEqual(quantum_program._semantic_role, "estimator_v2")

        # Verify job was returned
        self.assertEqual(job, self.mock_job)

    def test_run_with_pub_level_precision(self):
        """Test that EstimatorPub.coerce is called with precision parameter."""
        estimator = Estimator(mode=self.backend)
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
        estimator = Estimator(mode=self.backend)
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

        estimator = Estimator(mode=self.backend, options=options)
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
        estimator = Estimator(mode=self.backend)

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
        estimator = Estimator(mode=self.backend)
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
        estimator = Estimator(mode=self.backend)
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

        estimator = Estimator(mode=self.backend, options=options)

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

        estimator = Estimator(mode=self.backend, options=options)

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

        estimator = Estimator(mode=self.backend, options=options)

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
        estimator = Estimator(mode=self.backend)

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
        estimator = Estimator(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.metadata = {"test_key": "test_value"}

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        self.assertEqual(job, self.mock_job)

    def test_run_incompatible_broadcast_shapes(self):
        """Test that incompatible parameter and observable shapes raise an error."""
        estimator = Estimator(mode=self.backend)

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
        estimator = Estimator(mode=self.backend)

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
        estimator = Estimator(mode=self.backend)

        with self.assertRaisesRegex(IBMInputValueError, "No pubs provided"):
            estimator.run([])

        # Executor should never be reached
        self.mock_executor_instance.run.assert_not_called()

    def test_run_raises_error_when_pec_and_zne_both_enabled(self):
        """Test that run raises error when both pec_mitigation and zne_mitigation are enabled."""
        estimator = Estimator(mode=self.backend)
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


class TestEstimatorRunNoPatching(IBMTestCase):
    """Tests for the Estimator.run() method (with no Python methods patching)."""

    @mock_responses(OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry):
        """Estimator can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        estimator = Estimator(mode=backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable)], precision=0.03125, dry_run=True)
        self.assertEqual(job.backend().name, "mock_foo")

    @mock_responses
    def test_mode(self, registry):
        """Estimator `mode` and `backend()` is based on `mode` init argument."""
        service = QiskitRuntimeService(token="my_token")

        # Job mode, online backend.
        backend = service.backend("common_backend")
        estimator = Estimator(mode=backend)
        self.assertEqual(estimator.backend(), backend)
        self.assertEqual(estimator.mode, None)

        # Session mode.
        session = Session(backend)
        estimator = Estimator(mode=session)
        self.assertEqual(estimator.backend(), backend)
        self.assertEqual(estimator.mode, session)

        # Batch mode.
        batch = Batch(backend)
        estimator = Estimator(mode=batch)
        self.assertEqual(estimator.backend(), backend)
        self.assertEqual(estimator.mode, batch)

        # `None` mode (inside session).
        with Session(backend) as session:
            estimator = Estimator()
            self.assertEqual(estimator.backend(), backend)
            self.assertEqual(estimator.mode, session)


class TestEstimatorSimulatorMode(IBMTestCase):
    """Tests for Estimator with local simulator backends."""

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

        estimator = Estimator(mode=backend)
        estimator.options.default_shots = 10_000
        estimator.options.simulator.seed_simulator = 42
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

        estimator1 = Estimator(mode=backend)
        estimator1.options.default_shots = 100
        estimator1.options.simulator.seed_simulator = 42
        result1 = estimator1.run([(transpiled, observable)]).result()

        estimator2 = Estimator(mode=backend)
        estimator2.options.default_shots = 100
        estimator2.options.simulator.seed_simulator = 42
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

        estimator1 = Estimator(mode=backend)
        estimator1.options.default_shots = 100
        estimator1.options.simulator.seed_simulator = 42
        result1 = estimator1.run([(transpiled, observable)]).result()

        estimator2 = Estimator(mode=backend)
        estimator2.options.simulator.seed_simulator = 99
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
        estimator = Estimator(self.backend)
        estimator.options.resilience_level = 0

        finalized_options = estimator.finalize_options()
        self.assertFalse(finalized_options.twirling.enable_gates)
        self.assertFalse(finalized_options.twirling.enable_measure)
        self.assertFalse(finalized_options.resilience.measure_mitigation)
        self.assertFalse(finalized_options.resilience.zne_mitigation)

    def test_resilience_level_1(self):
        """Tests for resilience level 1."""
        estimator = Estimator(self.backend)
        estimator.options.resilience_level = 1

        finalized_options = estimator.finalize_options()
        self.assertFalse(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
        self.assertTrue(finalized_options.resilience.measure_mitigation)
        self.assertFalse(finalized_options.resilience.zne_mitigation)

    def test_resilience_level_2(self):
        """Tests for resilience level 2."""
        estimator = Estimator(self.backend)
        estimator.options.resilience_level = 2

        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
        self.assertTrue(finalized_options.resilience.measure_mitigation)
        self.assertTrue(finalized_options.resilience.zne_mitigation)

    @data(0, 1, 2)
    def test_set_values_are_preserved(self, resilience_level):
        """Test that when the user sets values, resilience level does not override them."""
        estimator = Estimator(self.backend)
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
        estimator = Estimator(self.backend)
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.measure_mitigation = True
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_measure)

        estimator = Estimator(self.backend)
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience.zne.amplifier = "pea"
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)

        estimator = Estimator(self.backend)
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.pec_mitigation = True
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)

    def test_no_warning_when_twirling_field_not_set_by_user(self):
        """No warning when the user never set the twirling field that is being overridden."""
        estimator = Estimator(self.backend)
        # Use resilience_level=0 so enable_measure defaults to False, ensuring the only
        # thing suppressing the warning is the field being absent from model_fields_set.
        estimator.options.resilience_level = 0
        estimator.options.resilience.measure_mitigation = True
        # enable_measure was not explicitly set by the user → no warning expected
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            estimator.finalize_options()
        user_warns = [w for w in caught if issubclass(w.category, UserWarning)]
        self.assertEqual(user_warns, [])

    def test_no_warning_when_user_set_field_to_true(self):
        """No warning when the user already set the field to True (no conflict)."""
        estimator = Estimator(self.backend)
        estimator.options.twirling.enable_measure = True
        estimator.options.resilience.measure_mitigation = True
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            estimator.finalize_options()
        user_warns = [w for w in caught if issubclass(w.category, UserWarning)]
        self.assertEqual(user_warns, [])

    def test_warning_measure_mitigation_overrides_enable_measure_false(self):
        """Warning when measure_mitigation=True overrides user-set enable_measure=False."""
        estimator = Estimator(self.backend)
        estimator.options.twirling.enable_measure = False
        estimator.options.resilience.measure_mitigation = True
        with self.assertWarns(UserWarning) as ctx:
            estimator.finalize_options()
        msg = str(ctx.warning)
        self.assertIn("enable_measure", msg)
        self.assertIn("measurement mitigation", msg)

    @data("enable_gates", "enable_measure")
    def test_warning_pea_overrides_twirling_field_false(self, field):
        """Warning when PEA overrides user-set enable_gates=False or enable_measure=False."""
        estimator = Estimator(self.backend)
        setattr(estimator.options.twirling, field, False)
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience.measure_mitigation = False
        estimator.options.resilience.zne.amplifier = "pea"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            estimator.finalize_options()
        msgs = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
        self.assertTrue(any(field in m and "PEA mitigation" in m for m in msgs))

    @data("enable_gates", "enable_measure")
    def test_warning_pec_overrides_twirling_field_false(self, field):
        """Warning when PEC overrides user-set enable_gates=False or enable_measure=False."""
        estimator = Estimator(self.backend)
        setattr(estimator.options.twirling, field, False)
        estimator.options.resilience.pec_mitigation = True
        estimator.options.resilience.measure_mitigation = False
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            estimator.finalize_options()
        msgs = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
        self.assertTrue(any(field in m and "PEC mitigation" in m for m in msgs))
