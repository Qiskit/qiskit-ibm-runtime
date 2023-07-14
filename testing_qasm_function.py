from qiskit_ibm_runtime.utils.qasm import validate_qasm_circuits

qasm = """
            OPENQASM 3.0;
            c[0] = measure qr[0];
            c[1] = measure qr[1];
"""

try:
    validate_qasm_circuits(qasm)
except Exception as e:
    print(e)
