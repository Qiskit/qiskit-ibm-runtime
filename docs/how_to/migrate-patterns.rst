Migrate code to Qiskit Runtime
==============================

In the following topics, we have identified key patterns of behavior and
use cases with code examples to help you migrate code to Qiskit
Runtime.  

.. note::
    
   The key to writing an equivalent algorithm using Qiskit Runtime primitives is to remove all dependencies on ``QuantumInstance`` and
``Backend`` and replacing them with the implementation of the ``BaseEstimator``, ``BaseSampler``, or both primitives from the ``qiskit_ibm_runtime`` library. 


It is also possible to use local implementations, as shown in the
`Amplitude estimation use case </how_to/migrate-e2e#amplitude>`__.

Notably, for common scenarios it is not necessary to handle backends
differently nor to construct expressions for expectation values
manually.
