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

"""Unit tests for EstimatorV2 prepare method."""

from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.executor import ExecutorOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMTestCase


@ddt
class TestPrepare(IBMTestCase):
    """Test the ``prepare`` function."""

    def test_vanilla_path(self):
        """Test the ``prepare`` function when no mitigation is requested."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.twirling.enable_measure = True

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [EstimatorPub.coerce((circuit, observable))]

        program, executor_options = prepare(pubs, options, shots=100)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        self.assertEqual(program.passthrough_data["post_processor"]["mitigation"], None)

    def test_pec_path(self):
        """Test the ``prepare`` function when PEC is requested."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.resilience.pec_mitigation = True
        options.resilience.noise_model_mapping = {
            "layer_0": PauliLindbladMap.identity(num_qubits=2)
        }

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [EstimatorPub.coerce((circuit, observable))]

        program, executor_options = prepare(pubs, options, shots=100)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        self.assertEqual(program.passthrough_data["post_processor"]["mitigation"], "pec")

    def test_zne_path(self):
        """Test the ``prepare`` function when PEC is requested."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.resilience.zne_mitigation = True

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [EstimatorPub.coerce((circuit, observable))]

        program, executor_options = prepare(pubs, options, shots=100)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        self.assertEqual(program.passthrough_data["post_processor"]["mitigation"], "zne")

    def test_pea_path(self):
        """Test the ``prepare`` function when PEA is requested."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.resilience.zne_mitigation = True
        options.resilience.zne.amplifier = "pea"

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [EstimatorPub.coerce((circuit, observable))]

        program, executor_options = prepare(pubs, options, shots=100)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        self.assertEqual(program.passthrough_data["post_processor"]["mitigation"], "pea")

    @data(True, False)
    def test_dd_applied_when_enabled(self, twirling_enabled):
        """Test apply_dynamical_decoupling is called when DD is enabled.

        Tests with twirling enabled and disabled (samplex item vs circuit item).
        """
        options = EstimatorOptions()
        options.dynamical_decoupling.enable = True
        options.twirling.enable_gates = twirling_enabled
        options.twirling.enable_measure = False

        # Create a circuit with a large delay on qubit 0.
        circuit = QuantumCircuit(3)
        for _ in range(10):
            circuit.cx(1, 2)
        circuit.cx(0, 1)
        observable = SparsePauliOp.from_list([("ZZZ", 1)])

        pubs = [
            EstimatorPub.coerce((circuit, observable)),
            EstimatorPub.coerce((circuit, observable)),
        ]

        program, _ = prepare(pubs, options, shots=100, backend=FakeManilaV2())

        # DD inserts X gates into idle slots of each circuit item
        for item in program.items:
            self.assertIn("x", item.circuit.count_ops())

    def test_dd_rejects_dynamic_circuits(self):
        """Test DD raises an error for circuits with control flow."""
        options = EstimatorOptions()
        options.dynamical_decoupling.enable = True

        circuit = QuantumCircuit(2, 1)
        circuit.h(0)
        circuit.measure(0, 0)
        circuit.if_else((0, True), QuantumCircuit(2, 1), QuantumCircuit(2, 1), [0, 1], [0])

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pubs = [EstimatorPub.coerce((circuit, observable))]

        with self.assertRaisesRegex(
            IBMInputValueError,
            "Dynamical decoupling is not compatible with dynamic circuits",
        ):
            prepare(pubs, options, shots=100, backend=FakeManilaV2())

    def test_dd_raises_when_no_backend(self):
        """Test DD raises an error when no backend is provided."""
        options = EstimatorOptions()
        options.dynamical_decoupling.enable = True

        circuit = QuantumCircuit(2)
        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pubs = [EstimatorPub.coerce((circuit, observable))]

        with self.assertRaisesRegex(
            IBMInputValueError,
            "A backend must be provided when dynamical decoupling is enabled",
        ):
            prepare(pubs, options, shots=100)
