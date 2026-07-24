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

from ddt import ddt
from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp

from qiskit_ibm_runtime.executor_estimator.prepare import prepare
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
