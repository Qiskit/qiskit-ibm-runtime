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

from unittest import mock
from unittest import skip

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.compiler import transpile
from ..utils import bell

from ..ibm_test_case import IBMIntegrationTestCase


class TestIBMQasmSimulator(IBMIntegrationTestCase):
    """Test IBM Quantum QASM Simulator."""

    def test_execute_one_circuit_simulator_online(self):
        """Test execute_one_circuit_simulator_online."""
        backend = self.service.get_backend("ibmq_qasm_simulator")
        quantum_register = QuantumRegister(1)
        classical_register = ClassicalRegister(1)
        quantum_circuit = QuantumCircuit(quantum_register, classical_register, name="qc")
        quantum_circuit.h(quantum_register[0])
        quantum_circuit.measure(quantum_register[0], classical_register[0])
        circs = transpile(quantum_circuit, backend=backend)
        shots = 1024
        job = backend.run(circs, shots=shots)
        result = job.result()
        counts = result.get_counts(quantum_circuit)
        target = {"0": shots / 2, "1": shots / 2}
        threshold = 0.1 * shots
        self.assert_dict_almost_equal(counts, target, threshold)

    def test_execute_several_circuits_simulator_online(self):
        """Test execute_several_circuits_simulator_online."""
        backend = self.service.get_backend("ibmq_qasm_simulator")
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
        job = backend.run(circs, shots=shots)
        result = job.result()
        counts1 = result.get_counts(qcr1)
        counts2 = result.get_counts(qcr2)
        target1 = {"00": shots / 4, "01": shots / 4, "10": shots / 4, "11": shots / 4}
        target2 = {"00": shots / 2, "11": shots / 2}
        threshold = 0.1 * shots
        self.assert_dict_almost_equal(counts1, target1, threshold)
        self.assert_dict_almost_equal(counts2, target2, threshold)

    def test_online_qasm_simulator_two_registers(self):
        """Test online_qasm_simulator_two_registers."""
        backend = self.service.get_backend("ibmq_qasm_simulator")
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
        job = backend.run(circs, shots=1024)
        result = job.result()
        result1 = result.get_counts(qcr1)
        result2 = result.get_counts(qcr2)
        self.assertEqual(result1, {"00 01": 1024})
        self.assertEqual(result2, {"10 00": 1024})

    @skip("TODO refactor to use backend._runtime_run")
    def test_new_sim_method(self):
        """Test new simulator methods."""

        def _new_submit(qobj, *args, **kwargs):
            # pylint: disable=unused-argument
            self.assertEqual(
                qobj.config.method, "extended_stabilizer", f"qobj header={qobj.header}"
            )
            return mock.MagicMock()

        backend = self.sim_backend

        sim_method = backend._configuration._data.get("simulation_method", None)
        submit_fn = backend._submit_job

        try:
            backend._configuration._data["simulation_method"] = "extended_stabilizer"
            backend._submit_job = _new_submit
            circ = transpile(bell(), backend=backend)
            backend.run(circ, header={"test": "circuits"})
        finally:
            backend._configuration._data["simulation_method"] = sim_method
            backend._submit_job = submit_fn

    @skip("TODO refactor to use backend._runtime_run")
    def test_new_sim_method_no_overwrite(self):
        """Test custom method option is not overwritten."""

        def _new_submit(qobj, *args, **kwargs):
            # pylint: disable=unused-argument
            self.assertEqual(qobj.config.method, "my_method", f"qobj header={qobj.header}")
            return mock.MagicMock()

        backend = self.sim_backend

        sim_method = backend._configuration._data.get("simulation_method", None)
        submit_fn = backend._submit_job

        try:
            backend._configuration._data["simulation_method"] = "extended_stabilizer"
            backend._submit_job = _new_submit
            circ = transpile(bell(), backend=backend)
            backend.run(circ, method="my_method", header={"test": "circuits"})
        finally:
            backend._configuration._data["simulation_method"] = sim_method
            backend._submit_job = submit_fn
