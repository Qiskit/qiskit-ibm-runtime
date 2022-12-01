Using Estimator in an algorithm
===============================

We consider an algorithm in pseudocode that requires a single estimation
from each of two pairs of quantum states and observables to produce the
result, for example, TrotterQRTE. In the code example without primitives, we see how a user would implement this
algorithm with the quantum instance in a case that covers both the
statevector simulator and a shot-based backend.

Code example without primitives
-------------------------------

.. code-block:: python

   from qiskit.providers import Backend
   from qiskit.utils import QuantumInstance
   from typing import Optional, Union
   from qiskit import QuantumCircuit
   from qiskit.opflow import OperatorBase

   class QuantumEstimationAlgorithm:

       def __init__(
           self,
           ...,
           quantum_instance: Optional[Union[QuantumInstance, Backend]],
       ) -> None:
           pass
       def _construct_state1(self, ...) -> QuantumCircuit:
           pass
       def _construct_state2(self, ...) -> QuantumCircuit:
           pass
       def _construct_observable1(self, ...) -> OperatorBase:
           pass
       def _construct_observable2(self, ...) -> OperatorBase:
           pass
       def _process_statevector_results(...):
           pass
      def  _process_qasm_results(...):
           pass
       def run_estimation_algorithm(self, ...):
           observable1 = self._construct_observable1(...)
           observable2 = self._construct_observable2(...)
           state1 = self._construct_state1(...)
           state2 = self._construct_state2(...)
    expectation1 = ~StateFn(observable1) @ StateFn(state1)
    expectation2 = ~StateFn(observable2) @ StateFn(state2)

           if self._quantum_instance.is_statevector:
               # run state on statevector simulator
               statevector = self._quantum_instance.execute([expectation1, expectation2]).get_statevector()
               estimations = self._process_statevector_results(...)
           else:
               # run state on QASM simulator or backend
               counts = self._quantum_instance.execute([expectation1, expectation2]).get_counts()
               estimations = self._process_qasm_results(...)

           return estimations



Code example updated to use primitives
--------------------------------------

.. code-block:: python

   from qiskit.primitives import BaseEstimator
   from qiskit import QuantumCircuit
   from qiskit.opflow import OperatorBase

   class QuantumEstimationAlgorithm:

       def __init__(
           self,
           ...,
           estimator: BaseEstimator,
       ) -> None:
           pass
       def _construct_state1(self, ...) -> QuantumCircuit:
           pass
       def _construct_state2(self, ...) -> QuantumCircuit:
           pass
       def _construct_observable1(self, ...) -> OperatorBase:
           pass
       def _construct_observable2(self, ...) -> OperatorBase:
           pass
       def run_estimation_algorithm(self, ...):
           state1 = self._construct_state1(...)
           state2 = self._construct_state2(...)
           observable1 = self._construct_observable1(...)
           observable2 = self._construct_observable2(...)
           estimated = self.estimator.run([state1, state2], [observable1, observable2])
           estimations = estimated.result().values
           return estimations



Related links
-------------

* `VQE implementation with estimator primitive code <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/time_evolvers/trotterization/trotter_qrte.py>`__
* `VQE implementation with estimator documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.time_evolvers.trotterization.TrotterQRTE.html#qiskit.algorithms.time_evolvers.trotterization.TrotterQRTE>`__
