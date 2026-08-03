# This code is part of Qiskit.
#
# (C) Copyright IBM 2020-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for fake backends."""

import operator
import unittest
from dataclasses import asdict

from ddt import data, ddt
from qiskit.circuit import QuantumCircuit
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.transpiler import generate_preset_pass_manager
from qiskit.utils import optionals
from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.fake_provider import (
    FakeManilaV2,
    FakeNairobiV2,
    FakeNighthawk,
    FakeProviderForBackendV2,
    FakeSherbrooke,
    FakeVigoV2,
)
from qiskit_ibm_runtime.options import EstimatorOptions, SamplerOptions

from ..decorators import production_only
from ..ibm_test_case import IBMIntegrationTestCase, IBMTestCase
from ..utils import combine

FAKE_PROVIDER_FOR_BACKEND_V2 = FakeProviderForBackendV2()


@ddt
class TestFakeBackends(IBMTestCase):
    """Test runnning circuits in fake backends.

    These tests are considered integration tests, even if they do not require network access, as
    they depend on `aer` and are time consuming.
    """

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        super().setUpClass()
        cls.circuit = QuantumCircuit(2)
        cls.circuit.h(0)
        cls.circuit.h(1)
        cls.circuit.h(0)
        cls.circuit.h(1)
        cls.circuit.x(0)
        cls.circuit.x(1)
        cls.circuit.measure_active()

    @data(*[be for be in FAKE_PROVIDER_FOR_BACKEND_V2.backends() if be.num_qubits > 1])
    def test_circuit_on_fake_backend_v2(self, backend):
        """Test running a circuit in fake backends."""
        if not optionals.HAS_AER and backend.num_qubits > 20:
            self.skipTest(f"Unable to run fake_backend {backend.backend_name} without qiskit-aer")
        backend.set_options(seed_simulator=42)
        pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        isa_circuit = pm.run(self.circuit)
        sampler = Sampler(backend)
        job = sampler.run([isa_circuit])
        pub_result = job.result()[0]
        counts = pub_result.data.meas.get_counts()
        max_count = max(counts.items(), key=operator.itemgetter(1))[0]
        self.assertEqual(max_count, "11")

    @data(0, 1, 2, 3)
    def test_circuit_on_fake_backend_v2_with_optimization_level(self, optimization_level):
        """Test running a circuit in a fake backend with different optimization level."""
        backend = FakeVigoV2()
        backend.set_options(seed_simulator=42)
        pm = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level)
        isa_circuit = pm.run(self.circuit)
        sampler = Sampler(backend)
        job = sampler.run([isa_circuit])
        pub_result = job.result()[0]
        counts = pub_result.data.meas.get_counts()
        max_count = max(counts.items(), key=operator.itemgetter(1))[0]
        self.assertEqual(max_count, "11")

    @unittest.skipUnless(optionals.HAS_AER, "qiskit-aer is required to run this test")
    def test_fake_nighthawk(self):
        """Test that submitting a simple circuit with FakeNighthawk works."""
        # Initialize fake_nighthawk
        backend = FakeNighthawk()
        self.assertEqual(backend.num_qubits, 120)

        # Assert backend property shapes are correct
        self.assertEqual(len(backend.properties().qubits), backend.num_qubits)

        # Initialize quantum circuit
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()

        # Transpile circuit against fake_nighthawk
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_circuit = pm.run(qc)

        self.assertEqual(isa_circuit.num_qubits, backend.num_qubits)

        # Run using local simulator
        sampler = Sampler(backend)
        job = sampler.run([isa_circuit])
        result = job.result()

        self.assertTrue(job.done())
        self.assertIsNotNone(result)

    @combine(
        opt_cls=[EstimatorOptions, SamplerOptions], fake_backend=[FakeManilaV2(), FakeNairobiV2()]
    )
    def test_simulator_set_backend(self, opt_cls, fake_backend):
        """Test Options.simulator.set_backend method."""
        options = opt_cls()
        options.simulator.seed_simulator = 42
        options.simulator.set_backend(fake_backend)

        noise_model = NoiseModel.from_backend(fake_backend)
        basis_gates = fake_backend.operation_names
        coupling_map = fake_backend.coupling_map

        self.assertEqual(options.simulator.coupling_map, coupling_map)
        self.assertEqual(options.simulator.noise_model, noise_model)

        expected_options = opt_cls()
        expected_options.simulator = {
            "noise_model": noise_model,
            "basis_gates": basis_gates,
            "coupling_map": coupling_map,
            "seed_simulator": 42,
        }

        self.assertDictEqual(asdict(options), asdict(expected_options))


class TestRefreshFakeBackends(IBMIntegrationTestCase):
    """Test case for refreshing fake backends."""

    @production_only
    def test_refresh_method(self):
        """Test refresh method."""
        # to verify the data files will be updated
        old_backend = FakeSherbrooke()
        # change some configuration
        old_backend.backend_version = "fake_version"

        service = QiskitRuntimeService(
            token=self.dependencies.token,
            channel=self.dependencies.channel,
            url=self.dependencies.url,
        )

        # This tests needs access to the real device, and it might not be available.
        try:
            service.backend("ibm_sherbrooke")
        except QiskitBackendNotFoundError:
            self.skipTest("Credentials do not have access to ibm_sherbrooke")

        with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
            old_backend.refresh(service)
        self.assertIn("The backend fake_sherbrooke has been updated", logs.output[1])

        # to verify the refresh can't be done
        wrong_backend = FakeSherbrooke()
        # set a non-existent backend name
        wrong_backend.backend_name = "wrong_fake_sherbrooke"
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            wrong_backend.refresh(service)
        self.assertIn("The refreshing of wrong_fake_sherbrooke has failed", logs.output[0])
