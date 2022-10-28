Use Sampler in an algorithm
===========================

We consider an algorithm in pseudocode that requires a single sample
from each of two quantum states to produce the result (Quantum
Amplitude/Phase Estimation). In the code example without primitives, we can see how a user would implement
this with a quantum instance in a case that covers both the statevector
simulator and a shot-based backend. 

Code example without primitives
-------------------------------

.. code-block:: python

   from qiskit.providers import Backend
   from qiskit.utils import QuantumInstance
   from typing import Optional, Union
   from qiskit import QuantumCircuit

   class QuantumSamplingAlgorithm:
       def __init__(
           self,
           ...,
           quantum_instance: Optional[Union[QuantumInstance, Backend]],
       ) -> None:
           pass
       def _construct_circuit1(self, ...) -> QuantumCircuit:
           pass
       def _construct_circuit2(self, ...) -> QuantumCircuit:
           pass
       def _process_statevector_results(...):
           pass
      def  _process_qasm_results(...):
           pass
       def run_sampling_algorithm(self, ...):

           if self._quantum_instance.is_statevector:
               # run circuit on statevector simulator
               circuit1 = self._construct_circuit1(..., measurement=False)
               circuit2 = self._construct_circuit2(..., measurement=False)
               statevector = self._quantum_instance.execute([circuit1, circuit2]).get_statevector()
               samples = self._process_statevector_results(...)
           else:
               # run circuit on QASM simulator or backend
               circuit1 = self._construct_circuit1(..., measurement=True)
               circuit2 = self._construct_circuit2(..., measurement=True)
               counts = self._quantum_instance.execute([circuit1, circuit2]).get_counts()
               samples = self._process_qasm_results(...)

           return samples



Code example updated to use primitives
--------------------------------------

.. code-block:: python

   from qiskit.primitives import BaseSampler
   from qiskit import QuantumCircuit

   class QuantumSamplingAlgorithm:
       def __init__(
           self,
           ...,
           sampler: BaseSampler,
       ) -> None:
           pass
       def _construct_circuit1(self, ...) -> QuantumCircuit:
           pass
       def _construct_circuit2(self, ...) -> QuantumCircuit:
           pass
       def run_sampling_algorithm(self, ...):
           circuit1 = self._construct_circuit1(...)
           circuit2 = self._construct_circuit2(...)
           sampled = sampler.run([circuit1, circuit2])
           samples = sampled.result().quasi_dists
           return samples



Related links
-------------

You can download the updated code here:

* `Phase estimators <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/phase_estimators/phase_estimation.py>`__  
* `Amplitude estimators <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/amplitude_estimators/ae.py>`__
