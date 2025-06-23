
from qiskit import QuantumCircuit, generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import FakeMidcircuit
from qiskit_ibm_runtime.circuit import MidCircuitMeasure
from qiskit.circuit import Measure


def create():
    circ = QuantumCircuit(2, 2)
    circ.append(MidCircuitMeasure(), [0], [0])
    circ.append(MidCircuitMeasure("measure_2"), [0], [1])
    circ.measure_all()
    print(circ.draw())
    print(circ.data)
    return circ

def transpile(circ, backend):
    pm = generate_preset_pass_manager(backend=backend)
    return pm.run(circ)

qc = create()

backend = FakeMidcircuit()
print(backend.target)
print(backend.operations)
print(backend.basis_gates)

out = transpile(qc, backend)
print(out.draw())
