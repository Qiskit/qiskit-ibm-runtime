# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Executor-based SamplerV2 V2."""
# pylint: disable=invalid-name

import unittest
from ddt import data, ddt, unpack

import numpy as np

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import real_amplitudes, UnitaryGate
from qiskit.primitives import PrimitiveResult, PubResult
from qiskit.primitives.containers import BitArray
from qiskit.primitives.containers.data_bin import DataBin
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerV2, SamplerOptions
from qiskit_ibm_runtime.exceptions import RuntimeJobFailureError
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from ....ibm_test_case import IBMIntegrationTestCase


@ddt
class TestSampler(IBMIntegrationTestCase):
    """Test SamplerV2"""

    def setUp(self):
        super().setUp()
        self.backend = self.service.backend(self.dependencies.qpu)

        self.fake_backend = FakeManilaV2()
        self._shots = 10000
        self._options = {"default_shots": 10000}
        pm = generate_preset_pass_manager(optimization_level=1, target=self.backend.target)
        self.pm = pm

    def test_sample_run_multiple_circuits(self):
        """Test SamplerV2.run() with multiple circuits."""
        circuit = QuantumCircuit(2, name="Bell")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        isa_circuit = self.pm.run(circuit)

        options = SamplerOptions()
        options.default_shots = 1000

        sampler = SamplerV2(self.backend, options)
        job = sampler.run([isa_circuit] * 3)

        results = job.result()

        self.assertIsInstance(results, PrimitiveResult)
        self.assertIsInstance(results.metadata, dict)
        self.assertEqual(len(results), 3)

        for result in results:
            self.assertIsInstance(result, PubResult)
            self.assertIsInstance(result.data, DataBin)
            self.assertIsInstance(result.metadata, dict)
            self.assertIsInstance(result.data.meas, BitArray)
            self.assertEqual(result.data.meas.num_shots, options.default_shots)

    def test_sampler_with_multiple_circuits(self):
        """Test sampler with multiple circuits."""
        circuit = QuantumCircuit(2, name="Bell")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        isa_circuit = self.pm.run(circuit)

        options = SamplerOptions()
        options.default_shots = 1000

        sampler = SamplerV2(self.backend, options)
        job = sampler.run([isa_circuit] * 3)

        results = job.result()

        self.assertIsInstance(results, PrimitiveResult)
        self.assertIsInstance(results.metadata, dict)
        self.assertEqual(len(results), 3)

        for result in results:
            self.assertIsInstance(result, PubResult)
            self.assertIsInstance(result.data, DataBin)
            self.assertIsInstance(result.metadata, dict)
            self.assertIsInstance(result.data.meas, BitArray)
            self.assertEqual(result.data.meas.num_shots, options.default_shots)

    @data(True, False)
    def test_sampler_with_parametric_circuits(self, twirling):
        """Test sampler with parametric circuits."""
        circuit = QuantumCircuit(2, name="Bell with Params")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.rz(Parameter("th"), 0)
        circuit.rz(Parameter("lam"), 1)
        circuit.measure_all()
        isa_circuit = self.pm.run(circuit)

        pub_shapes = [(5, 4), (3,)]
        num_parameters = isa_circuit.num_parameters
        pubs = [(isa_circuit, np.random.random(shape + (num_parameters,))) for shape in pub_shapes]

        options = SamplerOptions()
        options.twirling.enable_gates = twirling
        options.default_shots = 1000

        sampler = SamplerV2(self.backend, options)
        job = sampler.run(pubs)

        results = job.result()

        self.assertIsInstance(results, PrimitiveResult)
        self.assertIsInstance(results.metadata, dict)
        self.assertEqual(len(results), 2)

        for result, shape in zip(results, pub_shapes):
            self.assertEqual(result.data.meas.shape, shape)

    @data([1000, "auto", "auto", 1024], [1000, 5, "auto", 1000], [1000, 5, 3, 15])
    @unpack
    def test_sampler_num_shots(
        self, default_shots, num_randomizations, shots_per_randomization, num_shots
    ):
        """Test result's num_shots with different twirling options."""
        circuit = QuantumCircuit(2, name="Bell")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        isa_circuit = self.pm.run(circuit)

        options = SamplerOptions()
        options.twirling.enable_gates = True
        options.default_shots = default_shots
        options.twirling.num_randomizations = num_randomizations
        options.twirling.shots_per_randomization = shots_per_randomization

        sampler = SamplerV2(self.backend, options)
        job = sampler.run([isa_circuit])

        results = job.result()
        self.assertEqual(results[0].data.meas.num_shots, num_shots)
