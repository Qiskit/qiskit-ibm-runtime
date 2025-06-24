
from qiskit import QuantumCircuit, generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import FakeMidcircuit, FakeVigoV2
from qiskit_ibm_runtime.circuit import MidCircuitMeasure
from qiskit.circuit import Measure
from qiskit_ibm_runtime.transpiler.passes.basis.convert_mid_circ_meas import ConvertToMidCircuitMeasure
from qiskit.transpiler import PassManager
from qiskit_ibm_runtime import SamplerV2, QiskitRuntimeService
from my_info import CRN_INTERNAL

def create():
    print("\nCREATING CIRCUIT")
    circ = QuantumCircuit(2, 2)
    circ.x(0)
    # circ.append(MidCircuitMeasure(), [0], [0])
    circ.append(MidCircuitMeasure("measure_2"), [0], [1])
    circ.measure([0], [0])
    circ.measure_all()
    print(circ.draw())
    # print("Original circuit data:", circ.data)
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

# -----------
backend = FakeMidcircuit()
print("Backend basis gates:", backend.basis_gates)
print("Backend operations:")
for op in backend.operations:
    print("   ", op)

qc = create()
out_preset = transpile_preset(qc, backend)
out_custom = transpile_custom(qc, backend)

# -----------
backend = FakeVigoV2()
print("Backend basis gates:", backend.basis_gates)
print("Backend operations:")
for op in backend.operations:
    print("   ", op)

qc = create()
# out_preset = transpile_preset(qc, backend)
out_custom = transpile_custom(qc, backend)
