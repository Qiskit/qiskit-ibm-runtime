Migration guide
===========================================

.. _why-migrate:

Why use Qiskit Runtime?
--------------------------------------------

.. figure:: ../images/table.png
   :alt: table comparing backend.run to Qiskit Runtime primitives


**Benefits of using Qiskit Runtime**:

* Use Qiskit Runtime Primitives to simplify algorithm design and optimization. 
* Run circuits faster using sessions - a context manager designed to efficiently manage iterative workloads and minimize artificial latency between quantum and classical sub-components.
* Access our most powerful quantum systems with our latest performance and hardware optimization, including capabilities like error suppression and mitigation.
* Easily integrate Qiskit Runtime with your cloud or on-premise classical compute resources using the quantum serverless toolkit.

**Simplified interface**:

Use primitive programs to write code more efficiently.  For details, see the examples topics, such as `Using Estimator to design an algorithm <migrate-estimator>`__.

  .. figure:: ../images/compare-code.png
   :scale: 50 %
   :alt: Two code snippets, side by side
   :target: migrate-prim-based

   Code without primitives, and the same code after being rewritten to use primitives.


.. _migfaqs:

FAQs
--------------------------------------------

Users might have the followings questions when planning to migrate their
code to Qiskit Runtime.

.. raw:: html

  <details>
  <summary>Which channel should I use?</summary>

After deciding to use Qiskit Runtime primitives, the user must first decide whether their needs are better suited to using Qiskit Runtime
through IBM Cloud or IBM Quantum Platform.  Some information that might help in making this decision include:

* The available plans:

  * Qiskit Runtime is available in both the Open (free access) or Premium (contract-based paid access) plan of the IBM Quantum Platform. See `IBM Quantum access plans <https://www.ibm.com/quantum/access-plans>`__ for details.
  * Qiskit Runtime is accessible through the Lite (free access) or Standard (pay-as-you-go access) plan in IBM Cloud. See `Plans <../cloud/plans.html>`__ for details.

* The use case requirements:

  * IBM Quantum Platform offers a visual circuit composer (Quantum Composer) and a Jupyter Notebook environment (Quantum Lab).
  * IBM Cloud offers a cloud native service that is ideal if users need to integrate quantum capabilities with other cloud services.

.. raw:: html

   </details>

.. raw:: html

  <details>
  <summary>How do I set up my channel?</summary>

After deciding which channel to use to interact with Qiskit Runtime, you
can get set up on either platform using the instructions below:

To get started with Qiskit Runtime on IBM Quantum Platform, see
`Experiment with Qiskit Runtime <https://quantum-computing.ibm.com/services/resources/docs/resources/runtime/start>`__.

To get started with Qiskit Runtime on IBM Cloud, see the `Getting Started guide <../cloud/quickstart.html>`__.

.. raw:: html

   </details>

.. raw:: html

  <details>
  <summary>Should I modify the Qiskit Terra algorithms?</summary>

As of v0.22, `Qiskit Terra algorithms <https://github.com/Qiskit/qiskit-terra/tree/main/qiskit/algorithms>`__ use Qiskit Runtime primitives. Thus, there is no need for
users to modify amplitude estimators or any other Qiskit Terra
algorithms.

.. raw:: html

   </details>

.. raw:: html

  <details>
  <summary>Which primitive should I use?</summary>

When choosing which primitive to use, we first need to understand
whether our algorithm is supposed to use a quasi-probability
distribution sampled from a quantum state (a list of
quasi-probabilities), or an expectation value of a certain observable
with respect to a quantum state (a real number).

A probability distribution is often of interest in optimization problems
that return a classical bit string, encoding a certain solution to a
problem at hand. In these cases, we might be interested in finding a bit
string that corresponds to a ket value with the largest probability of
being measured from a quantum state, for example.

An expectation value of an observable could be the target quantity in
scenarios where the knowledge of a quantum state is not relevant. This
often occurs in optimization problems or chemistry applications, where
the extremal energy of a system is to be discovered, for example.

.. raw:: html

   </details>

.. raw:: html

  <details>
  <summary>Which parts of my code do I need to refactor?</summary>

Replace all dependencies on ``QuantumInstance`` and ``Backend`` with the
implementation of the ``Estimator``, ``Sampler``, or both
primitives from the ``qiskit_ibm_runtime`` library.

It is also possible to use local implementations, as shown in the
`Amplitude estimation use case <migrate-e2e#amplitude>`__.


.. raw:: html

   </details>

.. _mig_ex:

Code migration examples
--------------------------------------------

We have identified key patterns of behavior and use cases with code examples to help you migrate code to Qiskit Runtime.  

.. note::

   The key to writing an equivalent algorithm using Qiskit Runtime primitives is to remove all dependencies on ``QuantumInstance`` and ``Backend`` and replace them with the implementation of the Estimator, Sampler, or both primitives from the ``qiskit_ibm_runtime`` library. 

We use ``backend.run()`` in the examples, but anywhere backends are used, ``backend.run()`` could be replaced by ``QuantumInstance.execute()`` and the updated code would look the same.

Notably, for common scenarios it is not necessary to handle backends
differently nor to construct expressions for expectation values
manually.

We have examples for two basic situations:

1. Algorithm developers need to refactor algorithms to use primitives instead of backend.run.

   * `Update code that performs circuit sampling <migrate-sampler.html>`__
   * `Update code that calculates expectation values <migrate-estimator.html>`__
   
2. Algorithm users don't use primitives directly, but use Qiskit algorithms.  These users now need to pass in a primitive instead of a backend to the udpdated Qiskit algorithmes.

   * `Work with updated Qiskit algorithms <migrate-qiskit-alg.html>`__

The following topics are use cases with code migration examples:


* `Update parameter values while running <migrate-update-parm.html>`__
* `Primitive-based routines <migrate-prim-based.html>`__
* `End-to-end example <migrate-e2e.html>`__


Related links
-------------

* `Get started with Estimator <../tutorials/how-to-getting-started-with-estimator>`__
* `Get started with Sampler <../tutorials/how-to-getting-started-with-sampler>`__
