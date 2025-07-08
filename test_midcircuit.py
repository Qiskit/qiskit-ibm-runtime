
import io

from qiskit import QuantumCircuit, generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import FakeMidcircuit
from qiskit_ibm_runtime.circuit import MidCircuitMeasure
from qiskit.circuit import Measure
from qiskit_ibm_runtime.transpiler.passes.basis.convert_mid_circ_meas import ConvertToMidCircuitMeasure
from qiskit.transpiler import PassManager
from qiskit_ibm_runtime import SamplerV2, QiskitRuntimeService
from qiskit.qpy import dump, load
import qiskit.qasm3 as qasm3
from qiskit.qasm3 import DefcalInstruction
from my_info import CRN_INTERNAL
from qiskit.circuit.classical import expr, types

def create():
    print("\nCREATING CIRCUIT")
    circ = QuantumCircuit(2, 2)
    circ.x(0)
    circ.append(MidCircuitMeasure(), [0], [0])
    # circ.append(MidCircuitMeasure("measure_2"), [0], [1])
    circ.measure([0], [0])
    circ.measure_all()
    print(circ.draw())
    return circ

def transpile_custom(circ, backend):
    print("\nTRANSPILING CIRCUIT(custom pm)")
    custom_pass = ConvertToMidCircuitMeasure(backend.target)
    pm = PassManager([custom_pass])
    transpiled = pm.run(circ)
    print(transpiled.draw())
    # print("Post-custom circuit data:", transpiled.data)

def transpile_preset(circ, backend):
    print("\nTRANSPILING circuit (preset pm)")
    pm = generate_preset_pass_manager(backend=backend)
    transpiled = pm.run(circ)
    print(transpiled.draw())
    # print("Post-preset-pm circuit data:", transpiled.data)

def run_sampler(circ, backend):
    print("\nRUNNING SamplerV2")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", instance=CRN_INTERNAL)
    backend = service.backend("test_eagle_us-east")
    sampler = SamplerV2(mode=backend)
    result = sampler.run([circ]).result()[0].data
    print(result)

def qpy_roundtrip_qasm3_out(circ):
    print("QPY ROUNDTRIP")
    with io.BytesIO() as f:
        dump(circ, f)
        f.seek(0)
        out_circ = load(f)[0]
    print(out_circ.draw())

    print("QASM3 AFTER QPY")
    defcals = {
        "measure_2": DefcalInstruction("measure_2", 0, 1, types.Bool()),
    }
    
    qasm_str = qasm3.dumps(out_circ, implicit_defcals=defcals)
    return qasm_str

# -----------
backend = FakeMidcircuit()
print("Backend basis gates:", backend.basis_gates)
print("Backend operations:")
for op in backend.operations:
    print("   ", op)
print(backend.target)

qc = create()
out_preset = transpile_preset(qc, backend)
out_custom = transpile_custom(qc, backend)
qasm3_qc = qpy_roundtrip_qasm3_out(qc)
print(qasm3_qc)
