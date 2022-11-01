Why use the Qiskit Runtime execution model?
===========================================

Using Qiskit Runtime unlocks the following advantages:

* Run circuits faster with our cloud-native architecture that runs close to quantum hardware in low-latency, containerized compute environments. This architecture leads to significant performance enhancements, especially when considering variational quantum algorithms such as VQE, where loops between classical and quantum computation can be carried out with minimized latency.
* Use primitive programs to further abstract and simplify how you work with quantum hardware. Primitive programs provide methods that make it easier to build modular algorithms and other higher-order programs. Instead of simply returning counts, they return more immediately meaningful information.
* Access our most powerful and exploratory quantum systems with shorter wait times by creating and running quantum programs at scale.
* Allows seamless integrations with future functionality:

  * Expanded IBM Cloud access will allow users to couple Qiskit Runtime with other compute services while leveraging the efficiency of our quantum computing service architecture.
  * Qiskit Runtime will continue to expand support of key capabilities that enable research with Qiskit. For example, support of the ability to iterate on existing programs by allowing users to run programs with variations inputs and configurations, and offering intermediate results to individual executions.
  * Take advantage of seamless integration with the latest performance and hardware optimizations as we scale up and improve our offerings. With managed performance, users can quickly adopt our latest patterns and advances such as error suppression and mitigation, resulting in faster, higher-quality executions.
  * Upcoming primitive programs will allow easy access to future functionality, such as error suppression and mitigation.

Migrate code to Qiskit Runtime
------------------------------

We have identified key patterns of behavior and use cases with code examples to help you migrate code to Qiskit
Runtime.

.. note::

   The key to writing an equivalent algorithm using Qiskit Runtime primitives is to remove all dependencies on ``QuantumInstance`` and ``Backend`` and replacing them with the implementation of the ``BaseEstimator``, ``BaseSampler``, or both primitives from the ``qiskit_ibm_runtime`` library.

It is also possible to use local implementations, as shown in the
`Amplitude estimation use case <migrate-e2e#amplitude>`__.

Notably, for common scenarios it is not necessary to handle backends
differently nor to construct expressions for expectation values
manually.

The following topics are use cases with code migration examples:

* `Use Estimator in an algorithm </how_to/migrate-estimator>`__
* `Use Sampler in an algorithm </how_to/migrate-sampler>`__
* `Use Estimator and Sampler in an algorithm <how_to/migrate-est-sam>`__
* `Update parameter values while running <how_to/migrate-update-parm>`__
* `Primitive-based routines <how_to/migrate-prim-based>`__
* `End-to-end example <how_to/migrate-e2e>`__

Related links
-------------

* `Work with sessions <sessions>`__
* `Work with primitives <primitives>`__
