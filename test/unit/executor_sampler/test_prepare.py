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

"""Tests for the prepare function."""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.sampler_pub import SamplerPub

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_sampler.prepare import prepare
from qiskit_ibm_runtime.options_models import SamplerOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import CircuitItem, SamplexItem


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
        options = SamplerOptions(**{"twirling": {"enable_gates": False, "enable_measure": False}})
        program, executor_options = prepare(pubs, options)

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

    def test_binding_array_key_order_bound_by_circuit_parameters(self):
        """Parameter values must be ordered by ``circuit.parameters``.

        Regression: ``prepare`` used to call ``as_array()`` without passing the
        circuit's parameters, so a dict/BindingsArray whose key order differed
        from ``circuit.parameters`` bound values to the wrong parameters silently.
        """
        a = Parameter("a")
        b = Parameter("b")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(a, 0)
        circuit.rz(b, 0)
        circuit.measure(0, 0)
        # circuit.parameters is canonically sorted -> (a, b).
        self.assertEqual([p.name for p in circuit.parameters], ["a", "b"])

        # Key the bindings in the opposite order (b, a); intended a=0.1, b=0.7.
        pub = SamplerPub.coerce((circuit, {("b", "a"): [0.7, 0.1]}), shots=1024)

        # No-twirling path -> CircuitItem.circuit_arguments ordered (a, b).
        options = options = SamplerOptions(
            **{"twirling": {"enable_gates": False, "enable_measure": False}}
        )
        program, _ = prepare([pub], options, default_shots=1024)
        self.assertIsInstance(program.items[0], CircuitItem)
        np.testing.assert_array_equal(program.items[0].circuit_arguments, [0.1, 0.7])

        # Twirling path -> SamplexItem parameter_values ordered (a, b).
        options = options = SamplerOptions(
            **{"twirling": {"enable_gates": True, "enable_measure": True}}
        )
        program_tw, _ = prepare([pub], options, default_shots=1024)
        self.assertIsInstance(program_tw.items[0], SamplexItem)
        np.testing.assert_array_equal(
            np.asarray(program_tw.items[0].samplex_arguments["parameter_values"]).reshape(-1),
            [0.1, 0.7],
        )

    def test_default_shots(self):
        """Test that default shots are used when not specified in pub."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots specified
        options = SamplerOptions(**{"twirling": {"enable_gates": False, "enable_measure": False}})
        program, executor_options = prepare([pub], options, 123)

        self.assertEqual(program.shots, 123)
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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})

        with self.assertRaises(IBMInputValueError) as context:
            prepare(pubs, options)

        self.assertIn("same number of shots", str(context.exception))

    def test_no_shots_specified_raises_error(self):
        """Test that missing shots raises an error."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})

        with self.assertRaises(IBMInputValueError) as context:
            prepare([pub], options, default_shots=None)

        self.assertIn("Shots must be specified", str(context.exception))

    def test_pub_with_box_raises_error(self):
        """Test that a pub with a BoxOp raises an error."""
        circuit = QuantumCircuit(2, 2)
        with circuit.box():
            circuit.x(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions(**{"twirling": {"enable_gates": False, "enable_measure": False}})

        with self.assertRaises(IBMInputValueError) as context:
            prepare([pub], options)

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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})

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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
        options.max_execution_time = 500

        _, executor_options = prepare([pub], options)

        self.assertEqual(executor_options.environment.max_execution_time, 500)

    def test_prepare_maps_experimental_image(self):
        """Test that prepare correctly maps experimental.image."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
        options.experimental = {"image": "custom-runtime:v2"}

        _, executor_options = prepare([pub], options)

        self.assertEqual(executor_options.environment.image, "custom-runtime:v2")

    def test_prepare_extracts_meas_level_from_options(self):
        """Test that prepare extracts meas_level from options."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions(**{"twirling": {"enable_gates": False, "enable_measure": False}})
        options.execution.meas_type = "kerneled"

        quantum_program, _ = prepare([pub], options)

        self.assertEqual(quantum_program.meas_level, "kerneled")

    def test_prepare_uses_default_meas_level_when_unset(self):
        """Test that prepare uses 'classified' as default when meas_type is not set."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
        quantum_program, _ = prepare([pub], options)

        self.assertEqual(quantum_program.meas_level, "classified")

    def test_prepare_allows_experimental_image(self):
        """Test that prepare allows experimental.image."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
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
        options = SamplerOptions(**{"twirling": {"enable_gates": False, "enable_measure": False}})
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


class TestPrepareTwirling(unittest.TestCase):
    """Unit tests for prepare() method with twirling enabled."""

    def test_prepare_creates_samplex_items(self):
        """Test that prepare() creates SamplexItem objects when twirling is enabled."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        # Create pub and options
        pub = SamplerPub.coerce(circuit, shots=1024)
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
        options.twirling.enable_gates = True

        # Call prepare
        qp, _ = prepare([pub], options, default_shots=1024)

        # Verify SamplexItem was created
        self.assertEqual(len(qp.items), 1)
        self.assertIsInstance(qp.items[0], SamplexItem)

    @patch("qiskit_ibm_runtime.executor_sampler.prepare.build")
    @patch("qiskit_ibm_runtime.executor_sampler.prepare.generate_boxing_pass_manager")
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
                options = SamplerOptions(
                    **{"twirling": {"enable_gates": True, "enable_measure": True}}
                )
                options.twirling.enable_gates = enable_gates
                options.twirling.enable_measure = enable_measure

                prepare([pub], options, default_shots=1024)

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
                options = SamplerOptions(
                    **{"twirling": {"enable_gates": True, "enable_measure": True}}
                )
                options.twirling.enable_measure = True
                options.execution.meas_type = meas_type
                with self.assertRaisesRegex(IBMInputValueError, "not compatible"):
                    prepare([pub], options, default_shots=1024)

        # The same kerneled meas_type is allowed when measurement twirling is off.
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
        options.twirling.enable_measure = False
        options.execution.meas_type = "kerneled"
        prepare([pub], options, default_shots=1024)  # must not raise

    @patch("qiskit_ibm_runtime.executor_sampler.prepare.build")
    @patch("qiskit_ibm_runtime.executor_sampler.prepare.generate_boxing_pass_manager")
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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
        options.twirling.enable_gates = True

        prepare([pub], options, default_shots=1024)

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
                options = SamplerOptions(
                    **{"twirling": {"enable_gates": True, "enable_measure": True}}
                )
                options.twirling.enable_gates = True
                options.twirling.num_randomizations = num_rand
                options.twirling.shots_per_randomization = shots_per_rand

                qp, _ = prepare([pub], options, default_shots=pub_shots)

                # Verify QuantumProgram shots (should be shots_per_randomization)
                self.assertEqual(qp.shots, expected_qp_shots)
                # Verify SamplexItem shape (should be num_randomizations)
                self.assertEqual(qp.items[0].shape, expected_shape)

    @patch("qiskit_ibm_runtime.executor_sampler.prepare.build")
    @patch("qiskit_ibm_runtime.executor_sampler.prepare.generate_boxing_pass_manager")
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
                options = SamplerOptions(
                    **{"twirling": {"enable_gates": True, "enable_measure": True}}
                )
                options.twirling.enable_gates = True
                options.twirling.strategy = strategy  # type: ignore[assignment]

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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": True}})
        options.twirling.enable_gates = True

        qp, _ = prepare([pub1, pub2], options, default_shots=1024)

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
        options = SamplerOptions(
            **{"twirling": {"enable_gates": enable_gates, "enable_measure": False}}
        )

        qp, _ = prepare([pub], options, default_shots=1024)

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
        options = SamplerOptions(**{"twirling": {"enable_gates": True, "enable_measure": False}})
        options.default_shots = 2048
        options.twirling.strategy = "all"  # type: ignore[assignment]
        options.execution.meas_type = "kerneled"
        options.environment.log_level = "DEBUG"

        qp, _ = prepare([pub], options, default_shots=1024)

        # Verify options dictionary is present in passthrough_data
        self.assertIn("post_processor", qp.passthrough_data)
        self.assertIn("post_processor", qp.passthrough_data)
        self.assertEqual(qp._semantic_role, "sampler_v2")
        self.assertEqual(qp.passthrough_data["post_processor"]["version"], "v0.1")
        self.assertEqual(qp.passthrough_data["post_processor"]["twirling"], True)
        self.assertEqual(qp.passthrough_data["post_processor"]["meas_type"], "kerneled")
