Migrate code to Qiskit Runtime
==============================

We have identified key patterns of behavior and use cases with code examples to help you migrate code to Qiskit
Runtime.

.. note::

   The key to writing an equivalent algorithm using Qiskit Runtime primitives is to remove all dependencies on ``QuantumInstance`` and ``Backend`` and replacing them with the implementation of the ``BaseEstimator``, ``BaseSampler``, or both primitives from the ``qiskit_ibm_runtime`` library.

It is also possible to use local implementations, as shown in the
`Amplitude estimation use case <migrate-e2e#amplitude.html>`__.

Notably, for common scenarios it is not necessary to handle backends
differently nor to construct expressions for expectation values
manually.

The following topics are use cases with code migration examples:

* `Use Estimator in an algorithm <migrate-estimator.html>`__
* `Use Sampler in an algorithm <migrate-sampler.html>`__
* `Use Estimator and Sampler in an algorithm <migrate-est-sam.html>`__
* `Update parameter values while running <migrate-update-parm.html>`__
* `Primitive-based routines <migrate-prim-based.html>`__
* `End-to-end example <migrate-e2e.html>`__
