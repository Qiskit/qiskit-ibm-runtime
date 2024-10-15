# This code is part of Qiskit.
#
# (C) Copyright IBM 2023, 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Sampler V2."""
# pylint: disable=invalid-name

from __future__ import annotations

import unittest

import numpy as np

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import RealAmplitudes, UnitaryGate
from qiskit.primitives import PrimitiveResult, PubResult
from qiskit.primitives.containers import BitArray
from qiskit.primitives.containers.data_bin import DataBin
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from ..decorators import run_integration_test, production_only
from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import get_real_device


class TestSampler(IBMIntegrationTestCase):
    """Test Sampler"""

    def setUp(self):
        super().setUp()
        self._backend = self.service.backend(self.dependencies.qpu)
        self.fake_backend = FakeManilaV2()
        self._shots = 10000
        self._options = {"default_shots": 10000}
        # TODO: Re-add seed_simulator and re-enable verification once it's supported
        # self._options = {"default_shots": 10000, "seed_simulator": 123}
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)

        self._cases = []
        hadamard = QuantumCircuit(1, 1, name="Hadamard")
        hadamard.h(0)
        hadamard.measure(0, 0)
        self._cases.append((hadamard, None, {0: 5000, 1: 5000}))  # case 0

        bell = QuantumCircuit(2, name="Bell")
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()
        self._cases.append((bell, None, {0: 5000, 3: 5000}))  # case 1
        self._isa_bell = pm.run(bell)

        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc = transpile(circuits=pqc, backend=self.fake_backend)
        self._cases.append((pqc, [0] * 6, {0: 10000}))  # case 2
        self._cases.append((pqc, [1] * 6, {0: 168, 1: 3389, 2: 470, 3: 5973}))  # case 3
        self._cases.append((pqc, [0, 1, 1, 2, 3, 5], {0: 1339, 1: 3534, 2: 912, 3: 4215}))  # case 4
        self._cases.append((pqc, [1, 2, 3, 4, 5, 6], {0: 634, 1: 291, 2: 6039, 3: 3036}))  # case 5

        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()
        pqc2 = transpile(circuits=pqc2, backend=self.fake_backend)
        self._cases.append(
            (pqc2, [0, 1, 2, 3, 4, 5, 6, 7], {0: 1898, 1: 6864, 2: 928, 3: 311})
        )  # case 6

    @run_integration_test
    def test_sampler_run(self, service):
        """Test Sampler.run()."""

        with Session(service, self.dependencies.qpu) as session:
            _, _, target = self._cases[1]
            with self.subTest("single"):
                sampler = Sampler(mode=session, options=self._options)
                job = sampler.run([self._isa_bell])
                result = job.result()
                self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("single with param"):
                sampler = Sampler(mode=session, options=self._options)
                job = sampler.run([(self._isa_bell, ())])
                result = job.result()
                self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("single array"):
                sampler = Sampler(mode=session, options=self._options)
                job = sampler.run([(self._isa_bell, [()])])
                result = job.result()
                self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("multiple"):
                sampler = Sampler(mode=session, options=self._options)
                job = sampler.run([(self._isa_bell, [(), (), ()])])
                result = job.result()
                self._verify_result_type(
                    result, num_pubs=1, targets=[np.array([target, target, target])]
                )

    def test_sample_run_multiple_circuits(self):
        """Test Sampler.run() with multiple circuits."""
        _, _, target = self._cases[1]
        sampler = Sampler(mode=self._backend, options=self._options)
        result = sampler.run([self._isa_bell, self._isa_bell, self._isa_bell]).result()
        self._verify_result_type(result, num_pubs=3, targets=[np.array(target)] * 3)

    def test_sampler_run_with_parameterized_circuits(self):
        """Test Sampler.run() with parameterized circuits."""
        pqc1, param1, target1 = self._cases[4]
        pqc2, param2, target2 = self._cases[5]
        pqc3, param3, target3 = self._cases[6]

        sampler = Sampler(mode=self.fake_backend, options=self._options)
        result = sampler.run([(pqc1, param1), (pqc2, param2), (pqc3, param3)]).result()
        self._verify_result_type(
            result, num_pubs=3, targets=[np.array(target1), np.array(target2), np.array(target3)]
        )

    def test_run_1qubit(self):
        """test for 1-qubit cases"""
        qc = QuantumCircuit(1)
        qc.measure_all()
        qc2 = QuantumCircuit(1)
        qc2.x(0)
        qc2.measure_all()

        sampler = Sampler(mode=self._backend, options=self._options)
        result = sampler.run([qc, qc2]).result()
        self._verify_result_type(result, num_pubs=2)

    def test_run_2qubit(self):
        """test for 2-qubit cases"""
        qc0 = QuantumCircuit(2)
        qc0.measure_all()
        qc1 = QuantumCircuit(2)
        qc1.x(0)
        qc1.measure_all()
        qc2 = QuantumCircuit(2)
        qc2.x(1)
        qc2.measure_all()
        qc3 = QuantumCircuit(2)
        qc3.x([0, 1])
        qc3.measure_all()

        sampler = Sampler(mode=self._backend, options=self._options)
        result = sampler.run([qc0, qc1, qc2, qc3]).result()
        self._verify_result_type(result, num_pubs=4)

    @run_integration_test
    def test_run_single_circuit(self, service):
        """Test for single circuit case."""
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)
        with Session(service, self.dependencies.qpu) as session:
            sampler = Sampler(mode=session, options=self._options)

            with self.subTest("No parameter"):
                circuit, _, target = self._cases[1]
                param_target = [
                    (None, np.array(target)),
                    ((), np.array(target)),
                    ([], np.array(target)),
                    (np.array([]), np.array(target)),
                    (((),), np.array([target])),
                    (([],), np.array([target])),
                    ([[]], np.array([target])),
                    ([()], np.array([target])),
                    (np.array([[]]), np.array([target])),
                ]
                for param, target in param_target:
                    with self.subTest(f"{circuit.name} w/ {param}"):
                        result = sampler.run([(self._isa_bell, param)]).result()
                        self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("One parameter"):
                circuit = QuantumCircuit(1, 1, name="X gate")
                param = Parameter("x")
                circuit.ry(param, 0)
                circuit.measure(0, 0)
                param_target = [
                    ([np.pi], np.array({1: self._shots})),
                    ((np.pi,), np.array({1: self._shots})),
                    (np.array([np.pi]), np.array({1: self._shots})),
                    ([[np.pi]], np.array([{1: self._shots}])),
                    (((np.pi,),), np.array([{1: self._shots}])),
                    (np.array([[np.pi]]), np.array([{1: self._shots}])),
                ]
                for param, target in param_target:
                    with self.subTest(f"{circuit.name} w/ {param}"):
                        result = sampler.run([(pm.run(circuit), param)]).result()
                        self._verify_result_type(result, num_pubs=1)

            with self.subTest("More than one parameter"):
                circuit, param, target = self._cases[3]
                param_target = [
                    (param, np.array(target)),
                    (tuple(param), np.array(target)),
                    (np.array(param), np.array(target)),
                    ((param,), np.array([target])),
                    ([param], np.array([target])),
                    (np.array([param]), np.array([target])),
                ]
                for param, target in param_target:
                    with self.subTest(f"{circuit.name} w/ {param}"):
                        result = sampler.run([(pm.run(circuit), param)]).result()
                        self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

    def test_run_reverse_meas_order(self):
        """test for sampler with reverse measurement order"""
        x = Parameter("x")
        y = Parameter("y")

        qc = QuantumCircuit(3, 3)
        qc.rx(x, 0)
        qc.rx(y, 1)
        qc.x(2)
        qc.measure(0, 2)
        qc.measure(1, 1)
        qc.measure(2, 0)
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)

        sampler = Sampler(mode=self._backend, options=self._options)
        result = sampler.run([(pm.run(qc), [0, 0]), (pm.run(qc), [np.pi / 2, 0])]).result()
        self._verify_result_type(result, num_pubs=2)

    @run_integration_test
    def test_run_empty_parameter(self, service):
        """Test for empty parameter"""
        with Session(service, self._backend) as session:
            n = 5
            qc = QuantumCircuit(n, n - 1)
            qc.measure(range(n - 1), range(n - 1))
            sampler = Sampler(mode=session, options=self._options)
            with self.subTest("one circuit"):
                result = sampler.run([qc]).result()
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("two circuits"):
                result = sampler.run([qc, qc]).result()
                self._verify_result_type(result, num_pubs=2)

    @run_integration_test
    def test_run_numpy_params(self, service):
        """Test for numpy array as parameter values"""
        with Session(service, self.dependencies.qpu) as session:
            qc = RealAmplitudes(num_qubits=2, reps=2)
            qc.measure_all()
            qc = transpile(circuits=qc, backend=self._backend)
            k = 5
            params_array = np.random.rand(k, qc.num_parameters)
            params_list = params_array.tolist()
            sampler = Sampler(mode=session, options=self._options)
            target = sampler.run([(qc, params_list)]).result()

            with self.subTest("ndarray"):
                result = sampler.run([(qc, params_array)]).result()
                self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("split a list"):
                result = sampler.run([(qc, params) for params in params_list]).result()
                self._verify_result_type(
                    result, num_pubs=len(params_list), targets=[np.array(target)]
                )

    @run_integration_test
    def test_run_with_shots_option(self, service):
        """test with shots option."""
        with Session(service, self.dependencies.qpu) as session:
            _, _, _ = self._cases[1]
            shots = 100
            with self.subTest("init option"):
                sampler = Sampler(mode=session, options={"default_shots": shots})
                result = sampler.run([self._isa_bell]).result()
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("update option"):
                sampler = Sampler(mode=session)
                sampler.options.default_shots = shots
                result = sampler.run([self._isa_bell]).result()
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("run arg"):
                sampler = Sampler(mode=session)
                result = sampler.run(pubs=[self._isa_bell], shots=shots).result()
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("run arg"):
                sampler = Sampler(mode=session)
                result = sampler.run(pubs=[self._isa_bell], shots=shots).result()
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("pub-like"):
                sampler = Sampler(mode=session)
                result = sampler.run([(self._isa_bell, None, shots)]).result()
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("pub"):
                sampler = Sampler(mode=session)
                result = sampler.run([SamplerPub(self._isa_bell, shots=shots)]).result()
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("multiple pubs"):
                sampler = Sampler()
                shots1 = 100
                shots2 = 200
                result = sampler.run(
                    [
                        SamplerPub(self._isa_bell, shots=shots1),
                        SamplerPub(self._isa_bell, shots=shots2),
                    ]
                ).result()
                self.assertEqual(result[0].data.meas.num_shots, shots1)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots1)
                self.assertEqual(result[1].data.meas.num_shots, shots2)
                self.assertEqual(sum(result[1].data.meas.get_counts().values()), shots2)
                self._verify_result_type(result, num_pubs=2)

    def test_run_shots_result_size(self):
        """test with shots option to validate the result size"""
        n = 10
        qc = QuantumCircuit(n)
        qc.h(range(n))
        qc.measure_all()
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)
        sampler = Sampler(mode=self._backend, options=self._options)
        result = sampler.run([pm.run(qc)]).result()
        self.assertLessEqual(result[0].data.meas.num_shots, self._shots)
        self.assertEqual(sum(result[0].data.meas.get_counts().values()), self._shots)
        self._verify_result_type(result, num_pubs=1)

    def test_primitive_job_status_done(self):
        """test primitive job's status"""
        sampler = Sampler(mode=self._backend, options=self._options)
        job = sampler.run([self._isa_bell])
        _ = job.result()
        self.assertEqual(job.status(), "DONE")

    @run_integration_test
    def test_circuit_with_unitary(self, service):
        """Test for circuit with unitary gate."""
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)

        with Session(service, self.dependencies.qpu) as session:
            with self.subTest("identity"):
                gate = UnitaryGate(np.eye(2))

                circuit = QuantumCircuit(1)
                circuit.append(gate, [0])
                circuit.measure_all()

                sampler = Sampler(mode=session, options=self._options)
                result = sampler.run([pm.run(circuit)]).result()
                self._verify_result_type(result, num_pubs=1)

            with self.subTest("X"):
                gate = UnitaryGate([[0, 1], [1, 0]])

                circuit = QuantumCircuit(1)
                circuit.append(gate, [0])
                circuit.measure_all()

                sampler = Sampler(mode=session, options=self._options)
                result = sampler.run([pm.run(circuit)]).result()
                self._verify_result_type(result, num_pubs=1)

    def test_metadata(self):
        """Test for metatdata."""
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)
        qc, _, _ = self._cases[1]
        sampler = Sampler(mode=self._backend, options=self._options)
        result = sampler.run([pm.run(qc)]).result()
        self.assertEqual(result[0].data.meas.num_shots, self._shots)
        self._verify_result_type(result, num_pubs=1)

    @run_integration_test
    def test_circuit_with_multiple_cregs(self, service):
        """Test for circuit with multiple classical registers."""
        with Session(service, self.dependencies.qpu) as session:
            cases = []
            pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)

            # case 1
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            qc.measure([0, 1, 2, 2], [0, 2, 4, 5])
            target = {"a": {0: 5000, 1: 5000}, "b": {0: 5000, 2: 5000}, "c": {0: 5000, 6: 5000}}
            cases.append(("use all cregs", pm.run(qc), target))

            # case 2
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(5, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            qc.measure([0, 1, 2, 2], [0, 2, 4, 5])
            target = {
                "a": {0: 5000, 1: 5000},
                "b": {0: 2500, 2: 2500, 24: 2500, 26: 2500},
                "c": {0: 10000},
            }
            cases.append(("use only a and b", pm.run(qc), target))

            # case 3
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            qc.measure(1, 5)
            target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 5000, 4: 5000}}
            cases.append(("use only c", pm.run(qc), target))

            # case 4
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            qc.measure([0, 1, 2], [5, 5, 5])
            target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 5000, 4: 5000}}
            cases.append(("use only c multiple qubits", pm.run(qc), target))

            # case 5
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 10000}}
            cases.append(("no measure", pm.run(qc), target))

            for title, qc, target in cases:
                with self.subTest(title):
                    sampler = Sampler(mode=session, options=self._options)
                    result = sampler.run([qc]).result()
                    data = result[0].data
                    self.assertEqual(len(data), 3)
                    self._verify_result_type(result, num_pubs=1)

    def test_sampler_v2_options(self):
        """Test SamplerV2 options."""
        sampler = Sampler(mode=self._backend)
        sampler.options.default_shots = 4096
        sampler.options.execution.init_qubits = True
        sampler.options.execution.rep_delay = 0.00025

        _, _, target = self._cases[1]
        job = sampler.run([self._isa_bell])
        result = job.result()
        self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

    @production_only
    @run_integration_test
    def test_sampler_v2_dd(self, service):
        """Test SamplerV2 DD options."""
        real_device_name = get_real_device(service)
        real_device = service.backend(real_device_name)
        sampler = Sampler(mode=real_device)
        sampler.options.dynamical_decoupling.enable = True
        sampler.options.dynamical_decoupling.sequence_type = "XX"
        sampler.options.dynamical_decoupling.extra_slack_distribution = "middle"
        sampler.options.dynamical_decoupling.scheduling_method = "asap"

        bell, _, _ = self._cases[1]
        bell = transpile(bell, real_device)
        job = sampler.run([bell])
        result = job.result()
        self._verify_result_type(result, num_pubs=1)

    def _verify_result_type(self, result, num_pubs, targets=None):
        """Verify result type."""
        self.assertIsInstance(result, PrimitiveResult)
        self.assertIsInstance(result.metadata, dict)
        self.assertEqual(len(result), num_pubs)
        for idx, pub_result in enumerate(result):
            # TODO: We need to update the following test to check `SamplerPubResult`
            # when the server side is upgraded to Qiskit 1.1.
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertIsInstance(pub_result.metadata, dict)
            if targets:
                self.assertIsInstance(result[idx].data.meas, BitArray)


if __name__ == "__main__":
    unittest.main()
