# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test IBM Quantum online QASM simulator."""

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.compiler import transpile
from qiskit_ibm_runtime import SamplerV2

from ..ibm_test_case import IBMIntegrationTestCase


class TestIBMQasmSimulator(IBMIntegrationTestCase):
    """Test IBM Quantum QASM Simulator."""

    def test_execute_one_circuit_simulator_online(self):
        """Test execute_one_circuit_simulator_online."""
        backend = self.service.backend("ibmq_qasm_simulator")
        sampler = SamplerV2(backend)
        quantum_register = QuantumRegister(1)
        classical_register = ClassicalRegister(1)
        quantum_circuit = QuantumCircuit(quantum_register, classical_register, name="qc")
        quantum_circuit.h(quantum_register[0])
        quantum_circuit.measure(quantum_register[0], classical_register[0])
        circs = transpile(quantum_circuit, backend=backend)
        shots = 1024
        job = sampler.run([circs], shots=shots)
        pub_result = job.result()[0]
        counts = pub_result.data.c0.get_counts()
        target = {"0": shots / 2, "1": shots / 2}
        threshold = 0.1 * shots
        self.assert_dict_almost_equal(counts, target, threshold)

    def test_execute_several_circuits_simulator_online(self):
        """Test execute_several_circuits_simulator_online."""
        backend = self.service.backend("ibmq_qasm_simulator")
        sampler = SamplerV2(backend)
        quantum_register = QuantumRegister(2)
        classical_register = ClassicalRegister(2)
        qcr1 = QuantumCircuit(quantum_register, classical_register, name="qc1")
        qcr2 = QuantumCircuit(quantum_register, classical_register, name="qc2")
        qcr1.h(quantum_register)
        qcr2.h(quantum_register[0])
        qcr2.cx(quantum_register[0], quantum_register[1])
        qcr1.measure(quantum_register[0], classical_register[0])
        qcr1.measure(quantum_register[1], classical_register[1])
        qcr2.measure(quantum_register[0], classical_register[0])
        qcr2.measure(quantum_register[1], classical_register[1])
        shots = 1024
        circs = transpile([qcr1, qcr2], backend=backend)
        job = sampler.run(circs, shots=shots)
        pub_result = job.result()[0]
        pub_result2 = job.result()[1]
        counts = pub_result.data.c1.get_counts()
        counts2 = pub_result2.data.c1.get_counts()
        target1 = {"00": shots / 4, "01": shots / 4, "10": shots / 4, "11": shots / 4}
        target2 = {"00": shots / 2, "11": shots / 2}
        threshold = 0.1 * shots
        self.assert_dict_almost_equal(counts, target1, threshold)
        self.assert_dict_almost_equal(counts2, target2, threshold)

    def test_online_qasm_simulator_two_registers(self):
        """Test online_qasm_simulator_two_registers."""
        backend = self.service.backend("ibmq_qasm_simulator")
        sampler = SamplerV2(backend)
        qr1 = QuantumRegister(2)
        cr1 = ClassicalRegister(2)
        qr2 = QuantumRegister(2)
        cr2 = ClassicalRegister(2)
        qcr1 = QuantumCircuit(qr1, qr2, cr1, cr2, name="circuit1")
        qcr2 = QuantumCircuit(qr1, qr2, cr1, cr2, name="circuit2")
        qcr1.x(qr1[0])
        qcr2.x(qr2[1])
        qcr1.measure(qr1[0], cr1[0])
        qcr1.measure(qr1[1], cr1[1])
        qcr1.measure(qr2[0], cr2[0])
        qcr1.measure(qr2[1], cr2[1])
        qcr2.measure(qr1[0], cr1[0])
        qcr2.measure(qr1[1], cr1[1])
        qcr2.measure(qr2[0], cr2[0])
        qcr2.measure(qr2[1], cr2[1])
        circs = transpile([qcr1, qcr2], backend)
        job = sampler.run(circs, shots=1024)
        pub_result = job.result()[0]
        pub_result2 = job.result()[1]
        counts = pub_result.data.c2.get_counts()
        counts2 = pub_result2.data.c2.get_counts()
        self.assertEqual(counts, {"01": 1024})
        self.assertEqual(counts2, {"00": 1024})
