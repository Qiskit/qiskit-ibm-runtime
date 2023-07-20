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
"""Unit tests for QASM utils."""

from typing import List, Dict
from test.ibm_test_case import IBMTestCase

from qiskit import QuantumCircuit, QiskitError
from qiskit.qasm3 import QASM3ImporterError
from qiskit_ibm_runtime.utils.qasm import (
    parse_qasm_circuits,
    str_to_quantum_circuit,
)


class TestUtilsQasm(IBMTestCase):
    """Tests for the methods utils.qasm file."""

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
