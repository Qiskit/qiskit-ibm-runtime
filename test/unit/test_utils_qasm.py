"""Unit tests for QASM utils."""

from typing import List, Dict
from test.ibm_test_case import IBMTestCase

from qiskit import QuantumCircuit, QiskitError
from qiskit.qasm3 import QASM3ImporterError
from qiskit_ibm_runtime.utils.qasm import (
    validate_qasm_circuits,
    parse_qasm_circuits,
    str_to_quantum_circuit,
)


class TestUtilsQasm(IBMTestCase):
    """Tests for the methods utils.qasm file."""

    def test_valid_qasm2(self):
        """Test the qasm2 validation"""
        qasm2 = """
                OPENQASM 2.0;
                include "qelib1.inc";
                qreg q[3];
                creg c[3];
                h q[0];
                cz q[0],q[1];
                cx q[0],q[2];
                measure q[0] -> c[0];
                measure q[1] -> c[1];
                measure q[2] -> c[2];
            """
        converted = validate_qasm_circuits(circuits=qasm2)
        self.assertIsInstance(converted, List)
        self.assertIsInstance(converted[0], QuantumCircuit)

    def test_valid_qasm3(self):
        """Test the qasm3 validation"""
        qasm3 = """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            bit[3] c;
            h q[0];
            cz q[0], q[1];
            cx q[0], q[2];
            c[0] = measure q[0];
            c[1] = measure q[1];
            c[2] = measure q[2];
            """
        converted = validate_qasm_circuits(circuits=qasm3)
        self.assertIsInstance(converted, List)
        self.assertIsInstance(converted[0], QuantumCircuit)

    def test_valid_qasm3_parameters(self):
        """Test the qasm 3 validation"""
        qasm3_params = """
            OPENQASM 3;
            include "stdgates.inc";
            input angle theta1;
            input angle theta2;
            bit[3] c;
            qubit[3] q;
            rz(theta1) q[0];
            sx q[0];
            rz(theta2) q[0];
            cx q[0], q[1];
            h q[1];
            cx q[1], q[2];
            c[0] = measure q[0];
            c[1] = measure q[1];
            c[2] = measure q[2];
            """
        converted = validate_qasm_circuits(circuits=qasm3_params)
        self.assertIsInstance(converted, List)
        self.assertIsInstance(converted[0], QuantumCircuit)

    def test_valid_qasm3_dynamic(self):
        """Test the dynamic qasm3 validation"""
        qasm3_dynamic = """
                OPENQASM 3;
                include "stdgates.inc";
                bit[2] c;
                qubit[3] q;
                h q[0];
                cx q[0], q[1];
                c[0] = measure q[0];
                h q[0];
                cx q[0], q[1];
                c[1] = measure q[0];
                if (c[0]) {
                    x q[2];
                } else {
                    h q[2];
                    z q[2];
                }
            """
        converted = validate_qasm_circuits(circuits=qasm3_dynamic)
        self.assertIsInstance(converted, List)
        self.assertIsInstance(converted[0], QuantumCircuit)

    def test_multiple_qasm(self):
        """Test the validations of multiples qasm circuits"""
        qasm1 = """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            bit[3] c;
            h q[0];
            cz q[0], q[1];
            cx q[0], q[2];
            c[0] = measure q[0];
            c[1] = measure q[1];
            c[2] = measure q[2];
            """
        qasm2 = """
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[3];
            creg c[3];
            h q[0];
            cz q[0],q[1];
            cx q[0],q[2];
            measure q[0] -> c[0];
            measure q[1] -> c[1];
            measure q[2] -> c[2];
            """
        converted = validate_qasm_circuits(circuits=[qasm1, qasm2])
        self.assertIsInstance(converted, List)
        self.assertEqual(len(converted), 2)

    def test_invalid_qasm(self):
        """Test the validation of an invalids qasm circuits"""
        qasm1 = """
            random text
            """
        qasm2 = """
            OPENQASM 3.0;
            c[0] = measure qr[0];
            c[1] = measure qr[1];
        """
        qasm3 = """
            OPENQASM 3.0;
            as
        """
        self.assertRaises(QiskitError, validate_qasm_circuits, qasm1)
        self.assertRaises(QiskitError, validate_qasm_circuits, qasm2)
        self.assertRaises(QiskitError, validate_qasm_circuits, qasm3)

    def test_parse_qasm_circuit(self):
        """Test the parsing of a qasm circuit"""
        program = """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            bit[3] c;
            h q[0];
            cz q[0], q[1];
            cx q[0], q[2];
            c[0] = measure q[0];
            c[1] = measure q[1];
            c[2] = measure q[2];
            """
        circuits = parse_qasm_circuits(circuits=program)
        self.assertIsInstance(circuits, List)
        self.assertIsInstance(circuits[0], QuantumCircuit)

    def test_parse_qasm_circuits_list(self):
        """Test the parsing of a qasm circuit"""
        program = """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            bit[3] c;
            h q[0];
            cz q[0], q[1];
            cx q[0], q[2];
            c[0] = measure q[0];
            c[1] = measure q[1];
            c[2] = measure q[2];
            """
        circuit = QuantumCircuit(2)
        circuit.x(range(2))
        circuit.measure_all()
        circuits = parse_qasm_circuits(circuits=[program, circuit])
        self.assertIsInstance(circuits, List)
        self.assertIsInstance(circuits[0], QuantumCircuit)

    def test_parse_qasm_circuits_dict(self):
        """Test the parsing of a qasm circuit"""
        program = """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            bit[3] c;
            h q[0];
            cz q[0], q[1];
            cx q[0], q[2];
            c[0] = measure q[0];
            c[1] = measure q[1];
            c[2] = measure q[2];
            """
        circuits = parse_qasm_circuits(circuits={"qasm": program})
        self.assertIsInstance(circuits, Dict)
        self.assertIsInstance(circuits["qasm"], QuantumCircuit)

    def test_str_to_quantum_circuit(self):
        """Test the str to quantum circuit conversion"""
        qasm3 = """
            OPENQASM 3;
            include "stdgates.inc";
            qubit[3] q;
            bit[3] c;
            h q[0];
            cz q[0], q[1];
            cx q[0], q[2];
            c[0] = measure q[0];
            c[1] = measure q[1];
            c[2] = measure q[2];
            """
        qasm2 = """
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[3];
            creg c[3];
            h q[0];
            cz q[0],q[1];
            cx q[0],q[2];
            measure q[0] -> c[0];
            measure q[1] -> c[1];
            measure q[2] -> c[2];
            """
        qasm_invalid = """
            include "qelib1.inc";
            qreg q[30];
            creg c[3];
            h q[0];
            measure q[0] -> c[0];
            """
        qasm3_circuit = str_to_quantum_circuit(qasm3)
        self.assertIsInstance(qasm3_circuit, QuantumCircuit)
        qasm2_circuit = str_to_quantum_circuit(qasm2)
        self.assertIsInstance(qasm2_circuit, QuantumCircuit)
        self.assertRaises(QASM3ImporterError, str_to_quantum_circuit, qasm_invalid)
