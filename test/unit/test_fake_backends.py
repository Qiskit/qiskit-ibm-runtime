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

from ddt import ddt, data, idata, unpack

from qiskit.circuit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.utils import optionals
from qiskit.circuit.library import (
    CZGate,
    ECRGate,
)
from qiskit.circuit.library.standard_gates import get_standard_gate_name_mapping
from qiskit.transpiler import InstructionProperties, Target
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2 as Sampler

from qiskit_ibm_runtime.fake_provider import (
    FakeProviderForBackendV2,
    FakeMumbaiV2,
    FakeSherbrooke,
    FakePrague,
)
from ..ibm_test_case import IBMTestCase


FAKE_PROVIDER_FOR_BACKEND_V2 = FakeProviderForBackendV2()


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
            self.skipTest(f"Unable to run fake_backend {backend.backend_name} without qiskit-aer")
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
        # test unit/value consistency on roundtrip
        if hasattr(configuration, "rep_times"):
            config_dict = configuration.to_dict()
            roundtrip_config = configuration.from_dict(config_dict)
            self.assertEqual(configuration.rep_times, roundtrip_config.rep_times)
            
    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_backend_full_two_qubit_gate_mapping(self, backend):
        gate_map = get_standard_gate_name_mapping()
        target = backend.target

        two_qubit_gate_properties: list[dict[tuple[int, int], InstructionProperties]] = [
            properties for gate_name, properties in target.items() 
            if gate_name in gate_map and gate_map[gate_name].num_qubits == 2
        ]
        for properties in two_qubit_gate_properties:
            for (qubit_i, qubit_j) in properties.keys():
                self.assertTrue((qubit_j, qubit_i) in properties, f"Missing 2 qubit gate between qubits {qubit_j} and {qubit_i} in backend {backend.backend_name}")
                    
                    
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

    def test_backend_configuration_attributes(self):
        backend = FakeMumbaiV2()
        self.assertTrue(backend.dynamic_reprate_enabled)
        self.assertTrue(backend.rep_delay_range)
