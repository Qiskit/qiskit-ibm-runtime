# This code is part of Qiskit.
#
# (C) Copyright IBM 2020, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=missing-module-docstring

import itertools
import operator

from unittest import SkipTest
from ddt import ddt, data, idata, unpack

from qiskit.circuit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.utils import optionals
from qiskit.circuit.library import (
    CZGate,
    ECRGate,
)
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2 as Sampler

from qiskit_ibm_runtime.fake_provider import (
    FakeProviderForBackendV2,
    FakeProvider,
    FakeMumbaiV2,
    FakeSherbrooke,
    FakePrague,
)
from ..ibm_test_case import IBMTestCase, IBMIntegrationTestCase
from ..decorators import production_only

FAKE_PROVIDER_FOR_BACKEND_V2 = FakeProviderForBackendV2()
FAKE_PROVIDER = FakeProvider()


@ddt
class TestFakeBackends(IBMTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.circuit = QuantumCircuit(2)
        cls.circuit.h(0)
        cls.circuit.h(1)
        cls.circuit.h(0)
        cls.circuit.h(1)
        cls.circuit.x(0)
        cls.circuit.x(1)
        cls.circuit.measure_all()

    @idata(
        itertools.product(
            [be for be in FAKE_PROVIDER_FOR_BACKEND_V2.backends() if be.num_qubits > 1],
            [0, 1, 2, 3],
        )
    )
    @unpack
    def test_circuit_on_fake_backend_v2(self, backend, optimization_level):
        if not optionals.HAS_AER and backend.num_qubits > 20:
            self.skipTest("Unable to run fake_backend %s without qiskit-aer" % backend.backend_name)
        backend.set_options(seed_simulator=42)
        pm = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level)
        isa_circuit = pm.run(self.circuit)
        sampler = Sampler(backend)
        job = sampler.run([isa_circuit])
        pub_result = job.result()[0]
        counts = pub_result.data.meas.get_counts()
        max_count = max(counts.items(), key=operator.itemgetter(1))[0]
        self.assertEqual(max_count, "11")

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_to_dict_properties(self, backend):
        properties = backend.properties()
        if properties:
            self.assertIsInstance(backend.properties().to_dict(), dict)
        else:
            self.assertTrue(backend.configuration().simulator)

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_convert_to_target(self, backend):
        target = backend.target
        if target.dt is not None:
            self.assertLess(target.dt, 1e-6)

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_backend_v2_dtm(self, backend):
        if backend.dtm:
            self.assertLess(backend.dtm, 1e-6)

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_to_dict_configuration(self, backend):
        configuration = backend.configuration()
        if configuration.open_pulse:
            self.assertLess(configuration.dt, 1e-6)
            self.assertLess(configuration.dtm, 1e-6)
            for i in configuration.qubit_lo_range:
                self.assertGreater(i[0], 1e6)
                self.assertGreater(i[1], 1e6)
                self.assertLess(i[0], i[1])

            for i in configuration.meas_lo_range:
                self.assertGreater(i[0], 1e6)
                self.assertGreater(i[0], 1e6)
                self.assertLess(i[0], i[1])

            for i in configuration.rep_times:
                self.assertGreater(i, 0)
                self.assertLess(i, 1)

        self.assertIsInstance(configuration.to_dict(), dict)

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_defaults_to_dict(self, backend):
        if hasattr(backend, "defaults"):
            defaults = backend.defaults()
            if defaults:
                self.assertIsInstance(defaults.to_dict(), dict)

                for i in defaults.qubit_freq_est:
                    self.assertGreater(i, 1e6)
                    self.assertGreater(i, 1e6)

                for i in defaults.meas_freq_est:
                    self.assertGreater(i, 1e6)
                    self.assertGreater(i, 1e6)
        else:
            self.skipTest("Backend %s does not have defaults" % backend)

    def test_delay_circuit(self):
        backend = FakeMumbaiV2()
        qc = QuantumCircuit(2)  # pylint: disable=invalid-name
        qc.delay(502, 0, unit="ns")
        qc.x(1)
        qc.delay(250, 1, unit="ns")
        qc.measure_all()
        res = transpile(qc, backend)
        self.assertIn("delay", res.count_ops())

    def test_non_cx_tests(self):
        backend = FakePrague()
        self.assertIsInstance(backend.target.operation_from_name("cz"), CZGate)
        backend = FakeSherbrooke()
        self.assertIsInstance(backend.target.operation_from_name("ecr"), ECRGate)


class TestRefreshFakeBackends(IBMIntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        # pylint: disable=arguments-differ
        # pylint: disable=no-value-for-parameter
        super().setUpClass()

    @production_only
    def test_refresh_method(self):
        """Test refresh method"""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud account does not have real backends.")
        # to verify the data files will be updated
        old_backend = FakeSherbrooke()
        # change some configuration
        old_backend.backend_version = "fake_version"
        # set instance to none to access real backend
        self.service._account.instance = None

        with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
            old_backend.refresh(self.service)
        self.assertIn("The backend fake_sherbrooke has been updated", logs.output[0])

        # to verify the data files are currently updated that there is nothing to refresh
        # create another instance of FakeSherbrooke updated above
        new_backend = FakeSherbrooke()
        with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
            new_backend.refresh(self.service)
        self.assertIn("There are no available new updates for fake_sherbrooke", logs.output[0])

        # to verify the refresh can't be done
        wrong_backend = FakeSherbrooke()
        # set a non-existent backend name
        wrong_backend.backend_name = "wrong_fake_sherbrooke"
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            wrong_backend.refresh(self.service)
        self.assertIn("The refreshing of wrong_fake_sherbrooke has failed", logs.output[0])
