Primitive-based routines
========================

We consider primitive-based routines that use the primitives interfaces
but perform more complicated actions, such as fidelity and gradient
routines, and povm measurement. They accept basic primitives (Sampler
or Estimator) in the initializer and use them for calculations.

.. 
    I didn't understand the purpose of this how-to until after reading migrate-prim-based.rst. The code examples here are not primitive routines, since they don't use primitives. Instead, they are algorithms that use primitive routines. Which makes this how-to very confusing.

    I don't quite understand why there's a how-to on using primitive routines. If you're writing an algorithm that uses a fidelity routine, you shouldn't care how the routine was written (as long as it has the expected interface). It's the person who has to write said routine that needs to care.
..

Fidelity routine
------------------

Suppose that we have an algorithm that requires a calculation of quantum
states overlaps. To save us some work, we might use the higher-level
fidelity routine, such as pVQD or VQD, that accepts the Sampler
primitive.

.. 
    Comment from Jessie: this code example doesn't use Sampler
..

In the code example, we can see how a user
would implement this algorithm with the quantum instance in a case that
covers both the statevector simulator and a shot-based backend.

.. 
    Comment from Jessie: this code example doesn't use a quantum instance
..


Code example
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



Gradient routine
------------------

Suppose that we have an algorithm that requires a calculation of
gradients of quantum circuits, such as VarQite. To save us some work, we
might use the higher-level gradient routine that accepts the Estimator
primitive.

The code example illustrates how a user would
implement this algorithm with Estimator in a case that covers
both the statevector simulator and a shot-based backend.


Code example 
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
           gradient_routine: BaseEstimatorGradient
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
