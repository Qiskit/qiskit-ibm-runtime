Update parameter values of parametrized circuits during algorithm execution
===========================================================================

We consider an algorithm, such as VQE, that iteratively calls one of the
primitive programs (here, the Estimator) during its execution. 

Overview
--------

Using the estimator object for the calls allows the cloud backend to
recognize calls that originate from the same algorithm and to prioritize
their execution, making the overall algorithm execution time much
faster.

Since the algorithm uses the same parametrized quantum circuit with
different parameters in each call, the primitive is smart enough to
recognize it and perform quantum circuit transpilation only once, which
uses classical resources more efficiently. Moreover, only the updated
parameters are transferred to the cloud, saving additional bandwidth.

In the code example without primitives, we can see how
a user would implement the algorithm with the quantum instance in a case
that covers both the statevector simulator and a shot-based backend.

Code example without primitives
-------------------------------

.. code-block:: python

   from qiskit.providers import Backend
   from qiskit.utils import QuantumInstance
   from typing import Optional, Union
   from qiskit import QuantumCircuit
   from qiskit.opflow import OperatorBase

   class QuantumEstimationAlgorithmWithUpdates:
       def __init__(
           self,
           ...,
           quantum_instance: Optional[Union[QuantumInstance, Backend]],
       ) -> None:
           pass
       def _construct_parametrized_state(self, ...) -> QuantumCircuit:
           pass
       def _construct_observable(self, ...) -> OperatorBase:
           pass
       def _calculate_new_params(self, estimations, ...):
           pass
       def _is_finished(self, ...) -> bool:
           pass
       def run_estimation_algorithm(self, ...):
           state = self._construct_parametrized_state(...)
           observable = self._construct_observable(...)
           estimations = ...
           expectation = ~StateFn(observable) @ StateFn(state)
           while not self._is_finished(...):
               param_values = self._calculate_new_params(estimations, ...)
               bound_expectation = expectation.bind_parameters(param_values)
               if self._quantum_instance.is_statevector:
                   # run state on statevector simulator
                   statevector = self.quantum_instance.execute([bound_expectation]).get_statevector()
                   estimations = self._process_statevector_results(...)
               else:
                   # run state on QASM simulator or backend
                   # for real backends, each queues joins the end of the current device queue
                   counts = self.quantum_instance.execute([bound_expectation]).get_counts()
                   estimations = self._process_qasm_results(...)
           return estimations



Code example updated to use primitives
--------------------------------------

.. code-block:: python

   from qiskit.primitives import BaseEstimator
   from qiskit import QuantumCircuit

   class QuantumEstimationAlgorithmWithUpdates:
       def __init__(
           self,
           ...,
           estimator: BaseEstimator,
       ) -> None:
           pass
       def _construct_parametrized_state(self, ...) -> QuantumCircuit:
           pass
       def _construct_observable(self, ...) -> OperatorBase:
           pass
       def _calculate_new_params(self, estimations, ...):
           pass
       def _is_finished(self, ...) -> bool:
           pass
       def run_estimation_algorithm(self, ...):
           state = self._construct_parametrized_state(...)
           observable = self._construct_observable(...)
           estimations = ...

           while not self._is_finished(...):
               param_values = self._calculate_new_params(estimations, ...)
               # highly optimized queuing for calls that come from the same algorithm - no waiting at the end of the queue every time
               # the same circuit is used and only compiled/transpiled once for the whole algorithm execution - only parameters are changed
               estimated = self.estimator.run([state], [observable], [param_values])
               estimations = estimated.result().values

           return estimations



Related links
-------------

`VQE implementation with primitives <https://qiskit.org/documentation/stubs/qiskit.algorithms.minimum_eigensolvers.VQE.html#qiskit.algorithms.minimum_eigensolvers.VQE>`__
