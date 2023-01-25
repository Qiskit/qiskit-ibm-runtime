Parametrized Circuits With Primitives
================================

Overview
------------

Parametrized circuits are a commonly used tool for quantum algorithm design. `backend.run()` and `QuantumInstance.execute()` didn't take in parametrized circuits, but the primitives do. This, again, is a simplification of the interface, as it is no longer necessary to bind parameters to a circuit before its execution.

Example
---------
Let's define a parametrized circuit:

.. code-block:: python

   from qiskit.circuit import QuantumCircuit, ParameterVector

   n = 3
   thetas = ParameterVector('θ',n)

   qc = QuantumCircuit(n, 1)
   qc.h(0)

   for i in range(n-1):
       qc.cx(i, i+1)

   for i,t in enumerate(thetas):
       qc.rz(t, i)

   for i in reversed(range(n-1)):
       qc.cx(i, i+1)
    
   qc.h(0)
   qc.measure(0, 0)

   qc.draw()

We want to assign the following parameter values to the circuit:

.. code-block:: python

   import numpy as np
   theta_values = [np.pi/2, np.pi/2, np.pi/2]


Legacy
---------
Before the primitives, the parameter values had to be bound to their respective circuit parameters prior to calling `backend.run()`.

.. code-block:: python

   from qiskit import Aer

   bound_circuit = qc.bind_parameters(theta_values)
   bound_circuit.draw()

   backend = Aer.get_backend('aer_simulator')
   job = backend.run(bound_circuit)
   counts = job.result().get_counts()
   print(counts)

Primitives
------------
Now, the primitives take in parametrized circuits directly, together with the parameter values, and the parameter assignment operation can be performed more efficiently on the server side of the primitive.

This feature is particularly interesting when working with iterative algorithms, as the parametrized circuit remains unchanged between calls, while the parameter values change. The primitives are able to transpile once, and then cache the unbound circuit, using classical resources more efficiently. Moreover, only the updated parameters are transferred to the cloud, saving additional bandwidth.

.. code-block:: python

   from qiskit.primitives import Sampler

   sampler = Sampler()
   job = sampler.run(qc, theta_values)
   result = job.result().quasi_dists
   print(result)
