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
from unittest.mock import patch

import numpy as np
from ddt import data, ddt
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
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.session import Session

from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...registries import OneInstanceDryRunRegistry


@ddt
class TestEstimatorRun(IBMTestCase):
    """Tests for the Estimator.run() method."""

    @mock_responses
    def test_run_single_pub_no_parameters(self, registry):
        """Test run with single pub without parameters."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            job = estimator.run([(circuit, observable)], precision=0.03125)

        # Verify executor.run was called.
        run_spy.assert_called_once()

        # Verify the quantum program passed to executor.
        quantum_program = run_spy.call_args[0][1]
        self.assertIsInstance(quantum_program, QuantumProgram)
        # precision=0.03125 -> shots = ceil(1/0.03125^2) = 1024
        self.assertEqual(quantum_program.shots, 1024)

        # Verify that information needed for post-processing dispatch were attached.
        self.assertEqual(quantum_program._semantic_role, "estimator_v2")

        # Verify job was returned.
        self.assertEqual(job.primitive_id, "executor")

    @mock_responses
    def test_run_with_pub_level_precision(self, registry):
        """Test that EstimatorPub.coerce is called with precision parameter."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            job = estimator.run([(circuit, observable, None, 0.01)])

        run_spy.assert_called_once()
        # precision=0.01 -> shots = ceil(1/0.01^2) = 10000
        quantum_program = run_spy.call_args[0][1]
        self.assertEqual(quantum_program.shots, 10000)
        self.assertEqual(job.primitive_id, "executor")

    @mock_responses
    def test_run_uses_default_precision_from_options(self, registry):
        """Test that run uses default_precision from options when precision not specified."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))
        estimator.options.default_precision = 0.01
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            estimator.run([(circuit, observable)])

        # Verify executor.run was called.
        run_spy.assert_called_once()

        # Verify shots from precision were calculated.
        quantum_program = run_spy.call_args[0][1]
        self.assertEqual(quantum_program.shots, 10000)

    @mock_responses
    def test_run_precision_parameter_overrides_options(self, registry):
        """Test that precision parameter in run() overrides options.default_precision."""
        options = EstimatorOptions()
        options.default_precision = 0.022097  # sqrt(1/2048)

        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"), options=options)
        estimator.options.resilience_level = 0

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            estimator.run([(circuit, observable)], precision=0.015625)

        # Verify precision parameter was used instead of options.
        quantum_program = run_spy.call_args[0][1]
        # precision=0.015625 -> shots = ceil(1/0.015625^2) = 4096
        self.assertEqual(quantum_program.shots, 4096)

    @mock_responses
    def test_run_with_parametric_circuit(self, registry):
        """Test run with parametric circuit."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))

        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        circuit.rx(theta, 0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        parameter_values = np.array([[0], [np.pi / 2], [np.pi]])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            job = estimator.run([(circuit, observable, parameter_values)], precision=0.03125)

        run_spy.assert_called_once()
        self.assertEqual(job.primitive_id, "executor")

    @data(True, False)
    @mock_responses
    def test_run_multiple_pubs(self, measure_mitigation, registry):
        """Test run with multiple pubs."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))
        estimator.options.resilience.measure_mitigation = measure_mitigation
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)

        circuit2 = QuantumCircuit(3)
        circuit2.h([0, 1, 2])

        observable1 = SparsePauliOp.from_list([("ZZ", 1)])
        observable2 = SparsePauliOp.from_list([("ZZZ", 1)])

        pubs = [(circuit1, observable1), (circuit2, observable2)]

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            estimator.run(pubs, precision=0.03125)

        run_spy.assert_called_once()

        # Verify multiple items in quantum program.
        quantum_program = run_spy.call_args[0][1]
        self.assertEqual(len(quantum_program.items), 2 + measure_mitigation)

    @mock_responses
    def test_run_with_default_precision(self, registry):
        """Test that run uses the default precision value from options."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))
        estimator.options.resilience_level = 0
        # default_precision is 0.015625 by default.

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            estimator.run([(circuit, observable)])

        # Verify executor.run was called.
        run_spy.assert_called_once()

        # Verify shots from default precision were calculated.
        quantum_program = run_spy.call_args[0][1]
        # precision=0.015625 -> shots = ceil(1/0.015625^2) = 4096
        self.assertEqual(quantum_program.shots, 4096)

    @mock_responses
    def test_run_sets_executor_options(self, registry):
        """Test that run sets executor options correctly."""
        options = EstimatorOptions()
        options.execution.init_qubits = True
        options.execution.rep_delay = 0.001
        options.max_execution_time = 300

        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"), options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)], precision=0.03125)

        # Verify Executor was constructed with the correctly mapped executor options.
        self.mock_executor_class.assert_called_once()
        executor_options = self.mock_executor_class.call_args[1]["options"]
        self.assertTrue(executor_options.execution.init_qubits)
        self.assertEqual(executor_options.execution.rep_delay, 0.001)
        self.assertEqual(executor_options.max_execution_time, 300)

    @mock_responses
    def test_run_adds_options_to_passthrough_data(self, registry):
        """Test that run adds options, shots and precision to passthrough data."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.dynamical_decoupling.enable = False
        options.resilience.measure_mitigation = True

        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"), options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            estimator.run([(circuit, observable)], precision=0.03125)

        # Verify executor.run was called.
        run_spy.assert_called_once()

        # Verify passthrough data contains inputs and calculated values.
        quantum_program = run_spy.call_args[0][1]
        self.assertIsNotNone(quantum_program.passthrough_data)
        self.assertIn("post_processor", quantum_program.passthrough_data)
        post_processor_data = quantum_program.passthrough_data["post_processor"]
        self.assertIn("options", post_processor_data)
        self.assertIn("shots", post_processor_data)
        self.assertIn("precision", post_processor_data)

        # Verify options content.
        options_data = post_processor_data["options"]
        self.assertEqual(options_data["twirling"]["enable_gates"], True)
        self.assertEqual(options_data["dynamical_decoupling"]["enable"], False)
        self.assertEqual(options_data["resilience"]["measure_mitigation"], True)

    @mock_responses
    def test_run_passthrough_options_are_finalized_not_raw(self, registry):
        """Test that run adds finalized options (not user options) to passthrough data."""
        # measure_mitigation=True force-resolves twirling.enable_measure -> True; the user
        # leaves enable_gates / enable_measure / zne_mitigation unset (raw value None).
        options = EstimatorOptions()
        options.resilience.measure_mitigation = True

        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"), options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            estimator.run([(circuit, observable)], precision=0.03125)

        run_spy.assert_called_once()
        quantum_program = run_spy.call_args[0][1]
        options_metadata = quantum_program.passthrough_data["post_processor"]["options"]

        # Unset fields must echo their RESOLVED default, never None.
        self.assertIsNotNone(options_metadata["twirling"]["enable_gates"])
        self.assertEqual(options_metadata["twirling"]["enable_measure"], True)
        self.assertEqual(options_metadata["twirling"]["enable_gates"], False)
        self.assertEqual(options_metadata["resilience"]["zne_mitigation"], False)

    @mock_responses
    def test_run_with_multiple_observables(self, registry):
        """Test run with multiple observables in a single pub."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observables = [
            SparsePauliOp.from_list([("ZZ", 1)]),
            SparsePauliOp.from_list([("XX", 1)]),
            SparsePauliOp.from_list([("YY", 1)]),
        ]

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            job = estimator.run([(circuit, observables)], precision=0.03125)

        run_spy.assert_called_once()
        self.assertEqual(job.primitive_id, "executor")

    @mock_responses
    def test_run_preserves_circuit_metadata(self, registry):
        """Test that run preserves circuit metadata through the pipeline."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.metadata = {"test_key": "test_value"}

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        with patch.object(Executor, "run", autospec=True, wraps=Executor.run) as run_spy:
            job = estimator.run([(circuit, observable)], precision=0.03125)

        run_spy.assert_called_once()
        self.assertEqual(job.primitive_id, "executor")

    @mock_responses
    def test_run_incompatible_broadcast_shapes(self, registry):
        """Test that incompatible parameter and observable shapes raise an error."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))

        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        circuit.rx(theta, 0)
        circuit.cx(0, 1)

        # Create observables with shape (3,)
        observables = [{"ZZ": 1}, {"XX": 1}, {"YY": 1}]

        # Create parameter values with shape (2,) - incompatible with (3,)
        parameter_values = np.array([[0], [np.pi / 2]])

        # Should raise ValueError when trying to run with incompatible shapes.
        # The error will be raised during pub coercion in the run method.
        with self.assertRaises(ValueError) as context:
            estimator.run([(circuit, observables, parameter_values)], precision=0.03125)

        # Verify the error message mentions broadcasting incompatibility.
        self.assertIn("broadcastable", str(context.exception).lower())

    @mock_responses
    def test_run_mismatched_precision_raises_error(self, registry):
        """Test that pubs with different precision values raise an error."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Create pubs with different precision values.
        pub1 = EstimatorPub.coerce((circuit, observable), precision=0.01)
        pub2 = EstimatorPub.coerce((circuit, observable), precision=0.02)

        with self.assertRaises(IBMInputValueError) as context:
            estimator.run([pub1, pub2])
        self.assertIn("same precision", str(context.exception))

    @mock_responses
    def test_run_raises_error_when_no_pubs_provided(self, registry):
        """Test that run raises IBMInputValueError when called with an empty pub list."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))

        with patch.object(Executor, "run", wraps=Executor.run) as spy:
            with self.assertRaisesRegex(IBMInputValueError, "No pubs provided"):
                estimator.run([])

        # Executor should never be reached.
        spy.assert_not_called()

    @mock_responses
    def test_run_raises_error_when_pec_and_zne_both_enabled(self, registry):
        """Test that run raises error when both pec_mitigation and zne_mitigation are enabled."""
        service = QiskitRuntimeService(token="my_token")
        estimator = Estimator(mode=service.backend("common_backend"))
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


@ddt
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

    @data("job", "session", "batch")
    @mock_responses
    def test_mode_handling(self, mode_id, registry):
        """Estimator `mode` init argument should propagate to interface and through `run()`."""
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
                expected_session_id = "session_12345"
            case "batch":
                mode = Batch(backend)
                expected_mode = mode
                expected_session_id = "session_12345"

        # Public interfaces should respect `mode`.
        estimator = Estimator(mode=mode)
        self.assertEqual(estimator.backend(), backend)
        self.assertEqual(estimator.mode, expected_mode)

        # Jobs issued should belong to a session under `session` / `batch`` modes.
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable)], precision=0.03125)
        self.assertEqual(job._session_id, expected_session_id)


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

        # H|0> gives <Z>=0 with shot noise - results vary by seed.
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

    def test_resilience_level_0(self):
        """Tests for resilience level 0."""
        estimator = Estimator(GenericBackendV2(num_qubits=2))
        estimator.options.resilience_level = 0

        finalized_options = estimator.finalize_options()
        self.assertFalse(finalized_options.twirling.enable_gates)
        self.assertFalse(finalized_options.twirling.enable_measure)
        self.assertFalse(finalized_options.resilience.measure_mitigation)
        self.assertFalse(finalized_options.resilience.zne_mitigation)

    def test_resilience_level_1(self):
        """Tests for resilience level 1."""
        estimator = Estimator(GenericBackendV2(num_qubits=2))
        estimator.options.resilience_level = 1

        finalized_options = estimator.finalize_options()
        self.assertFalse(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
        self.assertTrue(finalized_options.resilience.measure_mitigation)
        self.assertFalse(finalized_options.resilience.zne_mitigation)

    def test_resilience_level_2(self):
        """Tests for resilience level 2."""
        estimator = Estimator(GenericBackendV2(num_qubits=2))
        estimator.options.resilience_level = 2

        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)
        self.assertTrue(finalized_options.resilience.measure_mitigation)
        self.assertTrue(finalized_options.resilience.zne_mitigation)

    @data(0, 1, 2)
    def test_set_values_are_preserved(self, resilience_level):
        """Test that when the user sets values, resilience level does not override them."""
        estimator = Estimator(GenericBackendV2(num_qubits=2))
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
        estimator = Estimator(GenericBackendV2(num_qubits=2))
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.measure_mitigation = True
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_measure)

        estimator = Estimator(GenericBackendV2(num_qubits=2))
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience.zne.amplifier = "pea"
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)

        estimator = Estimator(GenericBackendV2(num_qubits=2))
        estimator.options.resilience_level = resilience_level
        estimator.options.resilience.pec_mitigation = True
        finalized_options = estimator.finalize_options()
        self.assertTrue(finalized_options.twirling.enable_gates)
        self.assertTrue(finalized_options.twirling.enable_measure)

    def test_no_warning_when_twirling_field_not_set_by_user(self):
        """No warning when the user never set the twirling field that is being overridden."""
        estimator = Estimator(GenericBackendV2(num_qubits=2))
        # Use resilience_level=0 so enable_measure defaults to False, ensuring the only
        # thing suppressing the warning is the field being absent from model_fields_set.
        estimator.options.resilience_level = 0
        estimator.options.resilience.measure_mitigation = True
        # enable_measure was not explicitly set by the user → no warning expected.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            estimator.finalize_options()
        user_warns = [w for w in caught if issubclass(w.category, UserWarning)]
        self.assertEqual(user_warns, [])

    def test_no_warning_when_user_set_field_to_true(self):
        """No warning when the user already set the field to True (no conflict)."""
        estimator = Estimator(GenericBackendV2(num_qubits=2))
        estimator.options.twirling.enable_measure = True
        estimator.options.resilience.measure_mitigation = True
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            estimator.finalize_options()
        user_warns = [w for w in caught if issubclass(w.category, UserWarning)]
        self.assertEqual(user_warns, [])

    def test_warning_measure_mitigation_overrides_enable_measure_false(self):
        """Warning when measure_mitigation=True overrides user-set enable_measure=False."""
        estimator = Estimator(GenericBackendV2(num_qubits=2))
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
        estimator = Estimator(GenericBackendV2(num_qubits=2))
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
        estimator = Estimator(GenericBackendV2(num_qubits=2))
        setattr(estimator.options.twirling, field, False)
        estimator.options.resilience.pec_mitigation = True
        estimator.options.resilience.measure_mitigation = False
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            estimator.finalize_options()
        msgs = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
        self.assertTrue(any(field in m and "PEC mitigation" in m for m in msgs))
