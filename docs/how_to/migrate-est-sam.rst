Use Estimator and Sampler in an algorithm
=========================================

We consider an algorithm in pseudocode that combines scenarios from
these topics: `Use Estimator in an algorithm </how_to/migrate-estimator>`__
and `Use Sampler in an algorithm </how_to/migrate-sampler>`__
to produce the result. In the code example without primitives,
we can see how a user would implement this algorithm with the quantum
instance in a case that covers both the statevector simulator and a
shot-based backend.

.. _current-sam-est:

Code example without primitives
-------------------------------

.. code-block:: python

   from qiskit.providers import Backend
   from qiskit.utils import QuantumInstance
   from typing import Optional, Union
   from qiskit import QuantumCircuit
   from qiskit.opflow import OperatorBase

   class QuantumSamplingEstimationAlgorithm:
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
       def _construct_observable1(self, ...) -> OperatorBase:
           pass
       def _construct_observable2(self, ...) -> OperatorBase:
           pass
       def _process_statevector_results(...):
           pass
       def  _process_qasm_results(...):
           pass
       def sample(self, ...):
           if self._quantum_instance.is_statevector:
               # run circuit on statevector simulator
               circuit1 = self._construct_circuit1(..., measurement = False)
               circuit2 = self._construct_circuit2(..., measurement = False)
               statevector = self.quantum_instance.execute([circuit1, circuit2]).get_statevector()
               samples = self._process_statevector_results(...)
           else:
               # run circuit on QASM simulator or backend
               circuit1 = self._construct_circuit1(..., measurement = True)
               circuit2 = self._construct_circuit2(..., measurement = True)
               counts = self.quantum_instance.execute([circuit1, circuit2]).get_counts()
               samples = self._process_qasm_results(...)

           return samples

       def estimate(self, ...):
           observable1 = self._construct_observable1(...)
           observable2 = self._construct_observable2(...)
           state1 = self._construct_state1(...)
           state2 = self._construct_state2(...)
           expectation1 = ~StateFn(observable1) @ StateFn(state1)
           expectation2 = ~StateFn(observable2) @ StateFn(state2)

           if self._quantum_instance.is_statevector:
               # run state on statevector simulator
               statevector = self.quantum_instance.execute([expectation1, expectation2]).get_statevector()
               estimations = self._process_statevector_results(...)
           else:
               # run state on QASM simulator or backend
               counts = self.quantum_instance.execute([expectation1, expectation2]).get_counts()
               estimations = self._process_qasm_results(...)

           return estimations


   def run(self, ...):
   samples = self._sample(...)
   estimations = self._estimate(...)
   return samples, estimations



Code example updated to use primitives
--------------------------------------

.. code-block:: python

   from qiskit.primitives import BaseSampler, BaseEstimator
   from qiskit import QuantumCircuit
   from qiskit.opflow import OperatorBase

   class QuantumSamplingEstimationAlgorithm:
       def __init__(
          self,
          ...,
          sampler: BaseSampler,
          estimator: BaseEstimator,
       ) -> None:
          pass
       def _construct_circuit1(self, ...) -> QuantumCircuit:
          pass
       def _construct_circuit2(self, ...) -> QuantumCircuit:
          pass
       def _construct_observable1(self, ...) -> OperatorBase:
          pass
       def _construct_observable2(self, ...) -> OperatorBase:
          pass
       def _sample(self, ...):
          circuit1 = self._construct_circuit1(...)
          circuit2 = self._construct_circuit2(...)
          sampled = self.sampler.run([circuit1, circuit2])
          samples = sampled.result().quasi_dists

          return samples

       def _estimate(self, ...):
          state1 = self._construct_state1(...)
          state2 = self._construct_state2(...)
          observable1 = self._construct_observable1(...)
          observable2 = self._construct_observable2(...)
          estimated = self.estimator.run([state1, state2], [observable1, observable2])
          estimations = estimated.result().values

          return estimations

       def run(self, ...):
           samples = self._sample(...)
           estimations = self._estimate(...)
           return samples, estimations



Related links
-------------

* `VQD implementation with primitives code <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/eigen_solvers/vqd.py>`__
* `VQD implementation with primitives documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.VQD.html#qiskit.algorithms.VQD>`__
