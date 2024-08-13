# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the noise learner."""

from ddt import ddt

from qiskit import QuantumCircuit, transpile

from qiskit_ibm_runtime.noise_learner import NoiseLearner
from qiskit_ibm_runtime.options import NoiseLearnerOptions, EstimatorOptions
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from ..ibm_test_case import IBMTestCase
from ..utils import combine, get_mocked_backend


@ddt
class TestNoiseLearner(IBMTestCase):
    """Class for testing the NoiseLearner class."""

    def setUp(self):
        super().setUp()

        # A set of circuits
        c1 = QuantumCircuit(2)
        c1.cx(0, 1)

        c2 = QuantumCircuit(3)
        c2.cx(0, 1)
        c2.cx(1, 2)

        self.circuits = [c1, c2]

        # A set of non-trivial and equivalent options
        self.nl_options = NoiseLearnerOptions()
        self.nl_options.layer_pair_depths = [0, 2, 4]

        self.est_options = EstimatorOptions()
        self.est_options.resilience.layer_noise_learning.layer_pair_depths = [0, 2, 4]
        self.est_options.resilience_level = 2

        self.dict_options = {"layer_pair_depths": [0, 2, 4]}

    @combine(task_type=["circs", "pubs"], options_type=["learner", "estimator", "dict"])
    def test_run_program_inputs(self, task_type, options_type):
        """Test all supported tasks and options types."""
        backend = get_mocked_backend()

        if task_type == "circs":
            tasks = [transpile(c) for c in self.circuits]
        else:
            tasks = [(transpile(c), "Z" * c.num_qubits) for c in self.circuits]

        if options_type == "learner":
            options = self.nl_options
        elif options_type == "estimator":
            options = self.est_options
        else:
            options = self.dict_options

        inst = NoiseLearner(backend, options)
        inst.run(tasks)

        input_params = backend.service.run.call_args.kwargs["inputs"]
        self.assertEqual(input_params["circuits"], [transpile(c) for c in self.circuits])

        expected = self.dict_options
        expected["support_qiskit"] = True
        self.assertEqual(input_params["options"], expected)

    @combine(task_type=["circs", "pubs"])
    def test_run_program_inputs_with_default_options(self, task_type):
        """Test a circuit with default options."""
        backend = get_mocked_backend()

        if task_type == "circs":
            tasks = [transpile(c) for c in self.circuits]
        else:
            tasks = [(transpile(c), "Z" * c.num_qubits) for c in self.circuits]

        inst = NoiseLearner(backend)
        inst.run(tasks)

        input_params = backend.service.run.call_args.kwargs["inputs"]
        self.assertEqual(input_params["circuits"], [transpile(c) for c in self.circuits])
        self.assertEqual(input_params["options"], {"support_qiskit": True})

    def test_run_program_inputs_with_no_learnable_layers(self):
        """Test a circuit with no learnable layers."""
        backend = get_mocked_backend()

        inst = NoiseLearner(backend)
        inst.run([QuantumCircuit(3)])

        input_params = backend.service.run.call_args.kwargs["inputs"]
        self.assertIn("circuits", input_params)
        self.assertEqual(input_params["circuits"], [QuantumCircuit(3)])

    def test_irrelevant_options_are_ignored(self):
        """Test that irrelevant estimator options are ignored."""
        backend = get_mocked_backend()

        options = EstimatorOptions()
        options.default_shots = 10
        options.default_precision = 0.1
        options.resilience.layer_noise_learning.num_randomizations = 2

        expected = NoiseLearnerOptions()
        expected.num_randomizations = 2

        inst = NoiseLearner(backend, options)
        self.assertEqual(inst.options, expected)

    def test_not_supported_in_local_mode(self):
        """Test exception when circuits is not ISA."""
        with self.assertRaisesRegex(ValueError, "not currently supported in local mode"):
            NoiseLearner(FakeSherbrooke())
