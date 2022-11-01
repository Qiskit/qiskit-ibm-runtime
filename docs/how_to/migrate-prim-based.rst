Primitive-based routines
========================

We consider primitive-based routines that use the primitives interfaces
but perform more complicated actions, such as fidelity, gradient
primitives, and povm measurement. They accept basic primitives (Sampler
or Estimator) in the initializer and use them for calculations.

Fidelity primitive
------------------

Suppose that we have an algorithm that requires a calculation of quantum
states overlaps. To save us some work, we might use the higher-level
fidelity primitive, such as pVQD or VQD, that accepts the Sampler
primitive.

In the code example without primitives, we can see how a user
would implement this algorithm with the quantum instance in a case that
covers both the statevector simulator and a shot-based backend.

Code example without primitives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from qiskit.providers import Backend
   from qiskit.utils import QuantumInstance
   from qiskit.opflow import CircuitSampler, ExpectationBase, StateFn
   from typing import Optional, Union
   from qiskit import QuantumCircuit

   class QuantumFidelityAlgorithm:

       def __init__(
           self,
           ...,
           expectation: BaseExpectation,
           quantum_instance: Optional[Union[QuantumInstance, Backend]],
       ) -> None:
           if not isinstance(quantum_instance, QuantumInstance):
               quantum_instance = QuantumInstance(quantum_instance)
           self.sampler = CircuitSampler(quantum_instance)

       def _construct_state1(self, ...) -> QuantumCircuit:
           pass
       def _construct_state2(self, ...) -> QuantumCircuit:
           pass
       def run_fidelity_algorithm(self, ...):

           state1 = self._construct_state1(...)
           state2 = self._construct_state2(...)

           values1 = np.random.random(circuit.num_parameters)
           values2 = np.random.random(circuit.num_parameters)

           bound_state_circuit1 = state1.assign_parameters(values1)
           bound_state_circuit2 = state2.assign_parameters(values2)

           overlap = StateFn(bound_state_circuit1).adjoint() @ StateFn(bound_state_circuit2)

           converted_overlap = self.expectation.convert(overlap)

           sampled_overlap = self.sampler.convert(converted_overlap)

           return sampled_overlap.eval()



Code example with primitives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from qiskit.algorithms.state_fidelities import BaseStateFidelity
   from qiskit import QuantumCircuit

   #fidelity = ComputeUncompute(Sampler())
   class QuantumFidelityAlgorithm:

       def __init__(
           self,
           ...,
           fidelity: BaseStateFidelity,
       ) -> None:
           pass
       def _construct_state1(self, ...) -> QuantumCircuit:
           pass
       def _construct_state2(self, ...) -> QuantumCircuit:
           pass
       def run_fidelity_algorithm(self, ...):

           state1 = self._construct_state1(...)
           state2 = self._construct_state2(...)

           values1 = np.random.random(circuit.num_parameters)
           values2 = np.random.random(circuit.num_parameters)

           job = self.fidelity.run([state1], [state2], [values1], [values2])
           fidelity = job.result().fidelities

           return fidelity



Gradient primitive
------------------

Suppose that we have an algorithm that requires a calculation of
gradients of quantum circuits, such as VarQite. To save us some work, we
might use the higher-level gradient primitive that accepts the Estimator
primitive.

The code example without primitives illustrates how a user would
implement this algorithm with the quantum instance in a case that covers
both the statevector simulator and a shot-based backend.

To write an equivalent algorithm that uses Qiskit Runtime primitives,
first remove all dependencies on ``QuantumInstance`` and ``Backend``.
Next, replace them with one of the implementations of the
``BaseEstimatorGradient`` initialized with one of the Estimator
(``BaseEstimator``) primitives. The updated algorithm is shown in
:ref:`code-example-with-primitives-1`. In this case, it
is not necessary to manually construct the quantum circuits for
gradients or use the gradient framework from Qiskit Opflow.

.. _code-example-without-primitives-1:

Code example without primitives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from qiskit.providers import Backend
   from qiskit.utils import QuantumInstance
   from qiskit.opflow import CircuitSampler, ExpectationBase, StateFn, Gradient, CircuitGradient
   from typing import Optional, Union, Dict, List
   from qiskit.circuit import Parameter
   from qiskit import QuantumCircuit

   class QuantumGradientAlgorithm:

       def __init__(
           self,
           ...,
           expectation: ExpectationBase,
           grad_method: Union[str, CircuitGradient],
           quantum_instance: Optional[Union[QuantumInstance, Backend]],
       ) -> None:
           if not isinstance(quantum_instance, QuantumInstance):
               quantum_instance = QuantumInstance(quantum_instance)
           self.gradient = Gradient(grad_method)
           pass
       def _construct_state1(self, ...) -> QuantumCircuit:
           pass
       def _construct_operator1(self, ...) -> QuantumCircuit:
           pass
       def _get_gradient_params(self, ...) -> List[Parameter]:
               pass
       def _get_parameter_values(self, ...) -> List[float | complex]:
               pass
       def run_gradient_algorithm(self, ...) -> List[float | complex]:

           state1 = self._construct_state1(...)
           operator1 = self._construct_operator1(...)

           gradient_params = self._get_gradient_params(...)
           parameter_values = self._get_parameter_values(...)

           operator = StateFn(operator1, is_measurement=True) @ StateFn(state1)
           gradient_callable = self.gradient.gradient_wrapper(
               operator, gradient_params, self.quantum_instance, self.expectation
           )
           gradients = gradient_callable(parameter_values)

           return gradients



.. _code-example-with-primitives-1:

Code example with primitives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from qiskit.algorithms.gradients.base_estimator_gradient import BaseEstimatorGradient
   from typing import List
   from qiskit.circuit import Parameter
   from qiskit import QuantumCircuit

   #gradient = FiniteDiffEstimatorGradient(Estimator())
   class QuantumGradientAlgorithm:

       def __init__(
           self,
           ...,
           gradient_primitive: BaseEstimatorGradient
       ) -> None:
           pass
       def _construct_state1(self, ...) -> QuantumCircuit:
           pass
       def _construct_operator1(self, ...) -> QuantumCircuit:
           pass
       def _get_gradient_params(self, ...) -> List[Parameter]:
               pass
       def _get_parameter_values(self, ...) -> List[float | complex]:
               pass
       def run_gradient_algorithm(self, ...) -> List[float | complex]:

           state1 = self._construct_state1(...)
           operator1 = self._construct_operator1(...)

           gradient_params = self._get_gradient_params(...)
           parameter_values = self._get_parameter_values(...)

           gradients = gradient.run([state1], [operator1], parameter_values, gradient_params)
           gradients = job.result().gradients

           return gradients



Related links
-------------

* `State fidelities documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.state_fidelities.html#module-qiskit.algorithms.state_fidelities>`__
* `State fidelities code <https://github.com/Qiskit/qiskit-terra/tree/main/qiskit/algorithms/state_fidelities>`__
* `PVQD with primitives documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.PVQD.html#qiskit.algorithms.PVQD>`__
* `PVQD with primitives code <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/time_evolvers/pvqd/pvqd.py>`__
* `VQD with primitives documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.VQD.html#qiskit.algorithms.VQD>`__
* `VQD with primitives code <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/eigen_solvers/vqd.py>`__
* `Gradients documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.gradients.html#module-qiskit.algorithms.gradients>`__
* `Gradients code <https://github.com/Qiskit/qiskit-terra/tree/main/qiskit/algorithms/gradients>`__
