from qiskit import qasm3
from qiskit.circuit import QuantumCircuit

from qiskit_ibm_runtime.circuit.library import MidCircuitMeasure


measure_2 = MidCircuitMeasure("measure_2")
measure_3 = MidCircuitMeasure("measure_3")

circ = QuantumCircuit(2, 2)
circ.append(measure_2, [0], [0])
circ.append(measure_3, [1], [0])
circ.append(measure_2, [0], [1])
circ.measure_all()

print(qasm3.dumps(circ, annotation_handlers=MidCircuitMeasure.qasm3_annotation_handlers()))