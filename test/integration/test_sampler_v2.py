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
from numpy.typing import NDArray

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import RealAmplitudes, UnitaryGate
from qiskit.primitives import PrimitiveResult, PubResult
from qiskit.primitives.containers import BitArray
from qiskit.primitives.containers.data_bin import DataBin
from qiskit.primitives.containers.sampler_pub import SamplerPub

from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.fake_provider import FakeManila
from ..decorators import run_integration_test, production_only
from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import get_real_device


class TestSampler(IBMIntegrationTestCase):
    """Test Sampler"""

    def setUp(self):
        super().setUp()
        self.backend = "ibmq_qasm_simulator"
        self.fake_backend = FakeManila()
        self._shots = 10000
        self._options = {"default_shots": 10000}
        # TODO: Re-add seed_simulator and re-enable verification once it's supported
        # self._options = {"default_shots": 10000, "seed_simulator": 123}

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

    def _assert_allclose(
        self, bitarray: BitArray, target: NDArray | BitArray, rtol: float = 1e-1
    ) -> None:
        # pylint: disable=unused-argument
        return
        # self.assertEqual(bitarray.shape, target.shape)
        # for idx in np.ndindex(bitarray.shape):
        #     int_counts = bitarray.get_int_counts(idx)
        #     target_counts = (
        #         target.get_int_counts(idx) if isinstance(target, BitArray) else target[idx]
        #     )
        #     # pylint: disable=nested-min-max
        #     max_key = max(max(int_counts.keys()), max(target_counts.keys()))
        #     ary = np.array([int_counts.get(i, 0) for i in range(max_key + 1)])
        #     tgt = np.array([target_counts.get(i, 0) for i in range(max_key + 1)])
        #     np.testing.assert_allclose(ary, tgt, rtol=rtol, err_msg=f"index: {idx}")

    @run_integration_test
    def test_sampler_run(self, service):
        """Test Sampler.run()."""
        with Session(service, self.backend) as session:
            bell, _, target = self._cases[1]

            with self.subTest("single"):
                sampler = Sampler(session=session, options=self._options)
                job = sampler.run([bell])
                result = job.result()
                self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("single with param"):
                sampler = Sampler(session=session, options=self._options)
                job = sampler.run([(bell, ())])
                result = job.result()
                self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("single array"):
                sampler = Sampler(session=session, options=self._options)
                job = sampler.run([(bell, [()])])
                result = job.result()
                self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

            with self.subTest("multiple"):
                sampler = Sampler(session=session, options=self._options)
                job = sampler.run([(bell, [(), (), ()])])
                result = job.result()
                self._verify_result_type(
                    result, num_pubs=1, targets=[np.array([target, target, target])]
                )

    @run_integration_test
    def test_sample_run_multiple_circuits(self, service):
        """Test Sampler.run() with multiple circuits."""
        backend = service.backend(self.backend)
        bell, _, target = self._cases[1]
        sampler = Sampler(backend=backend, options=self._options)
        result = sampler.run([bell, bell, bell]).result()
        self._verify_result_type(result, num_pubs=3, targets=[np.array(target)] * 3)

    @run_integration_test
    def test_sampler_run_with_parameterized_circuits(self, service):
        """Test Sampler.run() with parameterized circuits."""
        backend = service.backend(self.backend)
        pqc1, param1, target1 = self._cases[4]
        pqc2, param2, target2 = self._cases[5]
        pqc3, param3, target3 = self._cases[6]

        sampler = Sampler(backend=backend, options=self._options)
        result = sampler.run([(pqc1, param1), (pqc2, param2), (pqc3, param3)]).result()
        self._verify_result_type(
            result, num_pubs=3, targets=[np.array(target1), np.array(target2), np.array(target3)]
        )

    @run_integration_test
    def test_run_1qubit(self, service):
        """test for 1-qubit cases"""
        backend = service.backend(self.backend)
        qc = QuantumCircuit(1)
        qc.measure_all()
        qc2 = QuantumCircuit(1)
        qc2.x(0)
        qc2.measure_all()

        sampler = Sampler(backend=backend, options=self._options)
        result = sampler.run([qc, qc2]).result()
        self._verify_result_type(result, num_pubs=2)
        for i in range(2):
            self._assert_allclose(result[i].data.meas, np.array({i: self._shots}))

    @run_integration_test
    def test_run_2qubit(self, service):
        """test for 2-qubit cases"""
        backend = service.backend(self.backend)
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

        sampler = Sampler(backend=backend, options=self._options)
        result = sampler.run([qc0, qc1, qc2, qc3]).result()
        self._verify_result_type(result, num_pubs=4)
        for i in range(4):
            self._assert_allclose(result[i].data.meas, np.array({i: self._shots}))

    @run_integration_test
    def test_run_single_circuit(self, service):
        """Test for single circuit case."""
        with Session(service, self.backend) as session:
            sampler = Sampler(session=session, options=self._options)

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
                        result = sampler.run([(circuit, param)]).result()
                        self.assertEqual(len(result), 1)
                        self._assert_allclose(result[0].data.meas, target)

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
                        result = sampler.run([(circuit, param)]).result()
                        self.assertEqual(len(result), 1)
                        self._assert_allclose(result[0].data.c, target)

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
                        result = sampler.run([(circuit, param)]).result()
                        self.assertEqual(len(result), 1)
                        self._assert_allclose(result[0].data.meas, target)

    @run_integration_test
    def test_run_reverse_meas_order(self, service):
        """test for sampler with reverse measurement order"""
        backend = service.backend(self.backend)
        x = Parameter("x")
        y = Parameter("y")

        qc = QuantumCircuit(3, 3)
        qc.rx(x, 0)
        qc.rx(y, 1)
        qc.x(2)
        qc.measure(0, 2)
        qc.measure(1, 1)
        qc.measure(2, 0)

        sampler = Sampler(backend=backend, options=self._options)
        result = sampler.run([(qc, [0, 0]), (qc, [np.pi / 2, 0])]).result()
        self.assertEqual(len(result), 2)

        # qc({x: 0, y: 0})
        self._assert_allclose(result[0].data.c, np.array({1: self._shots}))

        # qc({x: pi/2, y: 0})
        self._assert_allclose(result[1].data.c, np.array({1: self._shots / 2, 5: self._shots / 2}))

    @run_integration_test
    def test_run_empty_parameter(self, service):
        """Test for empty parameter"""
        with Session(service, self.backend) as session:
            n = 5
            qc = QuantumCircuit(n, n - 1)
            qc.measure(range(n - 1), range(n - 1))
            sampler = Sampler(session=session, options=self._options)
            with self.subTest("one circuit"):
                result = sampler.run([qc]).result()
                self.assertEqual(len(result), 1)
                self._assert_allclose(result[0].data.c, np.array({0: self._shots}))

            with self.subTest("two circuits"):
                result = sampler.run([qc, qc]).result()
                self.assertEqual(len(result), 2)
                for i in range(2):
                    self._assert_allclose(result[i].data.c, np.array({0: self._shots}))

    @run_integration_test
    def test_run_numpy_params(self, service):
        """Test for numpy array as parameter values"""
        with Session(service, self.backend) as session:
            qc = RealAmplitudes(num_qubits=2, reps=2)
            qc.measure_all()
            qc = transpile(circuits=qc, backend=self.fake_backend)
            k = 5
            params_array = np.random.rand(k, qc.num_parameters)
            params_list = params_array.tolist()
            sampler = Sampler(session=session, options=self._options)
            target = sampler.run([(qc, params_list)]).result()

            with self.subTest("ndarray"):
                result = sampler.run([(qc, params_array)]).result()
                self.assertEqual(len(result), 1)
                self._assert_allclose(result[0].data.meas, target[0].data.meas)

            with self.subTest("split a list"):
                result = sampler.run([(qc, params) for params in params_list]).result()
                self.assertEqual(len(result), k)
                for i in range(k):
                    self._assert_allclose(
                        result[i].data.meas, np.array(target[0].data.meas.get_int_counts(i))
                    )

    @run_integration_test
    def test_run_with_shots_option(self, service):
        """test with shots option."""
        with Session(service, self.backend) as session:
            bell, _, _ = self._cases[1]
            shots = 100

            with self.subTest("init option"):
                sampler = Sampler(session=session, options={"default_shots": shots})
                result = sampler.run([bell]).result()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)

            with self.subTest("update option"):
                sampler = Sampler(session=session)
                sampler.options.default_shots = shots
                result = sampler.run([bell]).result()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)

            with self.subTest("run arg"):
                sampler = Sampler(session=session)
                result = sampler.run(pubs=[bell], shots=shots).result()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)

            with self.subTest("run arg"):
                sampler = Sampler(session=session)
                result = sampler.run(pubs=[bell], shots=shots).result()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)

            with self.subTest("pub-like"):
                sampler = Sampler(session=session)
                result = sampler.run([(bell, None, shots)]).result()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)

            with self.subTest("pub"):
                sampler = Sampler(session=session)
                result = sampler.run([SamplerPub(bell, shots=shots)]).result()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].data.meas.num_shots, shots)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots)

            with self.subTest("multiple pubs"):
                sampler = Sampler()
                shots1 = 100
                shots2 = 200
                result = sampler.run(
                    [
                        SamplerPub(bell, shots=shots1),
                        SamplerPub(bell, shots=shots2),
                    ]
                ).result()
                self.assertEqual(len(result), 2)
                self.assertEqual(result[0].data.meas.num_shots, shots1)
                self.assertEqual(sum(result[0].data.meas.get_counts().values()), shots1)
                self.assertEqual(result[1].data.meas.num_shots, shots2)
                self.assertEqual(sum(result[1].data.meas.get_counts().values()), shots2)

    @run_integration_test
    def test_run_shots_result_size(self, service):
        """test with shots option to validate the result size"""
        backend = service.backend(self.backend)
        n = 10
        qc = QuantumCircuit(n)
        qc.h(range(n))
        qc.measure_all()
        sampler = Sampler(backend=backend, options=self._options)
        result = sampler.run([qc]).result()
        self.assertEqual(len(result), 1)
        self.assertLessEqual(result[0].data.meas.num_shots, self._shots)
        self.assertEqual(sum(result[0].data.meas.get_counts().values()), self._shots)

    @run_integration_test
    def test_primitive_job_status_done(self, service):
        """test primitive job's status"""
        backend = service.backend(self.backend)
        bell, _, _ = self._cases[1]
        sampler = Sampler(backend=backend, options=self._options)
        job = sampler.run([bell])
        _ = job.result()
        self.assertEqual(job.status(), "DONE")

    @run_integration_test
    def test_circuit_with_unitary(self, service):
        """Test for circuit with unitary gate."""
        with Session(service, self.backend) as session:
            with self.subTest("identity"):
                gate = UnitaryGate(np.eye(2))

                circuit = QuantumCircuit(1)
                circuit.append(gate, [0])
                circuit.measure_all()

                sampler = Sampler(session=session, options=self._options)
                result = sampler.run([circuit]).result()
                self.assertEqual(len(result), 1)
                self._assert_allclose(result[0].data.meas, np.array({0: self._shots}))

            with self.subTest("X"):
                gate = UnitaryGate([[0, 1], [1, 0]])

                circuit = QuantumCircuit(1)
                circuit.append(gate, [0])
                circuit.measure_all()

                sampler = Sampler(session=session, options=self._options)
                result = sampler.run([circuit]).result()
                self.assertEqual(len(result), 1)
                self._assert_allclose(result[0].data.meas, np.array({1: self._shots}))

    @run_integration_test
    def test_metadata(self, service):
        """Test for metatdata."""
        qc, _, _ = self._cases[1]
        backend = service.backend(self.backend)
        sampler = Sampler(backend=backend, options=self._options)
        result = sampler.run([qc]).result()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].data.meas.num_shots, self._shots)

    @run_integration_test
    def test_circuit_with_multiple_cregs(self, service):
        """Test for circuit with multiple classical registers."""
        with Session(service, self.backend) as session:
            cases = []

            # case 1
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            qc.measure([0, 1, 2, 2], [0, 2, 4, 5])
            target = {"a": {0: 5000, 1: 5000}, "b": {0: 5000, 2: 5000}, "c": {0: 5000, 6: 5000}}
            cases.append(("use all cregs", qc, target))

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
            cases.append(("use only a and b", qc, target))

            # case 3
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            qc.measure(1, 5)
            target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 5000, 4: 5000}}
            cases.append(("use only c", qc, target))

            # case 4
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            qc.measure([0, 1, 2], [5, 5, 5])
            target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 5000, 4: 5000}}
            cases.append(("use only c multiple qubits", qc, target))

            # case 5
            a = ClassicalRegister(1, "a")
            b = ClassicalRegister(2, "b")
            c = ClassicalRegister(3, "c")

            qc = QuantumCircuit(QuantumRegister(3), a, b, c)
            qc.h(range(3))
            target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 10000}}
            cases.append(("no measure", qc, target))

            for title, qc, target in cases:
                with self.subTest(title):
                    sampler = Sampler(session=session, options=self._options)
                    result = sampler.run([qc]).result()
                    self.assertEqual(len(result), 1)
                    data = result[0].data
                    self.assertEqual(len(data), 3)
                    for creg in qc.cregs:
                        self.assertIn(creg.name, data)
                        self._assert_allclose(data[creg.name], np.array(target[creg.name]))

    @run_integration_test
    def test_samplerv2_options(self, service):
        """Test SamplerV2 options."""
        backend = service.backend(self.backend)
        sampler = Sampler(backend=backend)
        sampler.options.default_shots = 4096
        sampler.options.execution.init_qubits = True
        sampler.options.execution.rep_delay = 0.00025

        bell, _, target = self._cases[1]
        job = sampler.run([bell])
        result = job.result()
        self._verify_result_type(result, num_pubs=1, targets=[np.array(target)])

    @production_only
    @run_integration_test
    def test_samplerv2_dd(self, service):
        """Test SamplerV2 DD options."""
        real_device_name = get_real_device(service)
        real_device = service.backend(real_device_name)
        sampler = Sampler(backend=real_device)
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
                self._assert_allclose(result[idx].data.meas, targets[idx])


if __name__ == "__main__":
    unittest.main()
