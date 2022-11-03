Considerations for Qiskit Runtime migration
============================================

Users might have the followings questions when planning to migrate their
code to Qiskit Runtime.

For general FAQs for Qiskit Runtime, see `FAQs for Qiskit Runtime <../faqs>`__.

Should I use Qiskit Runtime through IBM Cloud or IBM Quantum Platform?
----------------------------------------------------------------------

After deciding to use Qiskit Runtime primitives, the user must first decide whether their needs are better suited to using Qiskit Runtime
through IBM Cloud or IBM Quantum Platform.  Some information that might help in making this decision include:

* The available plans:

  * Qiskit Runtime is available in both the Open or Premium plan of the IBM Quantum Platform. See `IBM Quantum access plans <https://www.ibm.com/quantum/access-plans>`__ for details.
  * Qiskit Runtime is accessible through the Lite or Standard plan in IBM Cloud. See `Plans <../cloud/plans>`__ for details.

* The use case requirements:

  * IBM Quantum Platform offers a visual circuit composer (Quantum Composer) and a Jupyter Notebook environment (Quantum Lab).
  * IBM Cloud offers a cloud native service that is ideal if users need to integrate quantum capabilities with other cloud services.


How do I start using IBM Cloud or IBM Quantum Platform?
-------------------------------------------------------

After deciding which channel to use to interact with Qiskit Runtime, you
can get set up on either platform using the instructions below:

To get started with Qiskit Runtime on IBM Quantum Platform, see
`Experiment with Qiskit Runtime <https://quantum-computing.ibm.com/services/resources/docs/resources/runtime/start>`__.

To get started with Qiskit Runtime on IBM Cloud, see the `Getting Started guide <../cloud/quickstart>`__.

Should I modify the Qiskit Terra algorithms to use Qiskit Runtime primitives?
-----------------------------------------------------------------------------

As of v0.22, `Qiskit Terra algorithms <https://github.com/Qiskit/qiskit-terra/tree/main/qiskit/algorithms>`__ use Qiskit Runtime primitives. Thus, there is no need for
users to modify amplitude estimators or any other Qiskit Terra
algorithms.

Which primitive should I use?
-----------------------------

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

Which parts of my code do I need to refactor to use Qiskit Runtime?
-------------------------------------------------------------------

Replace all dependencies on ``QuantumInstance`` and ``Backend`` with the
implementation of the ``BaseEstimator``, ``BaseSampler``, or both
primitives from the ``qiskit_ibm_runtime`` library.

It is also possible to use local implementations, as shown in the
`Amplitude estimation use case <migrate-e2e#amplitude>`__

Notably, for common scenarios it is not necessary to handle backends
differently nor to construct expressions for expectation values
manually.
