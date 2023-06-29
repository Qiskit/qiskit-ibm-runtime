Introduction to primitives
=============================

With Qiskit Runtime, we are introducing a new set of interfaces, in the form of primitives, to expand on how users run jobs on quantum computers.

The existing Qiskit interface to backends (`backend.run()`) was originally designed to accept a list of circuits and return counts for every job. Over time, it became clear that users have diverse purposes for quantum computing, and therefore the ways in which they define the requirements for their computing jobs are expanding. Therefore, their results also look different.

For example, an algorithm researcher and developer cares about information beyond counts; they are more focused on efficiently calculating quasiprobabilities and expectation values of observables.

Our primitives provide methods that make it easier to build modular algorithms and other higher-order programs. Rather than simply returning counts, they return more immediately meaningful information. Additionally, they provide a seamless way to access the latest optimizations in IBM Quantum hardware and software.

The basic operations that one can perform with a probability distribution is to sample from it or to estimate quantities on it. Therefore, these operations form the fundamental building blocks of quantum algorithm development. Our first two Qiskit Runtime primitives (Sampler and Estimator) use these sampling and estimating operations as core interfaces to our quantum systems.

Available primitives
--------------------

The following primitives are available:


+-----------------------+-----------------------+------------------------------------+
| Primitive             | Description           | Example output                     |
+=======================+=======================+====================================+
| Estimator             | Allows a user to      | .. image:: images/estimator.png    |
|                       | specify a list of     |                                    |
|                       | circuits and          |                                    |
|                       | observables and       |                                    |
|                       | selectively group     |                                    |
|                       | between the lists to  |                                    |
|                       | efficiently evaluate  |                                    |
|                       | expectation values    |                                    |
|                       | and variances for a   |                                    |
|                       | parameter input. It   |                                    |
|                       | is designed to enable |                                    |
|                       | users to efficiently  |                                    |
|                       | calculate and         |                                    |
|                       | interpret expectation |                                    |
|                       | values of quantum     |                                    |
|                       | operators that are    |                                    |
|                       | required for many     |                                    |
|                       | near-term quantum     |                                    |
|                       | algorithms.           |                                    |
+-----------------------+-----------------------+------------------------------------+
| Sampler               | Generates             |                                    |
|                       | quasiprobability      |                                    |
|                       | distributions from    |                                    |
|                       | input circuits.       |                                    |
|                       | This enables the      |                                    |
|                       | return of error       |                                    |
|                       | mitigated samples,    |                                    |
|                       | enhancing the output  |                                    |
|                       | for sampling          |                                    |
|                       | algorithms            |                                    |
|                       | such as amplitude     |                                    |
|                       | amplification.        |                                    |
+-----------------------+-----------------------+------------------------------------+


How to use primitives
---------------------

Primitive interfaces vary based on the type of task that you want to run on the quantum computer and the corresponding data that you want returned as a result. After identifying the appropriate primitive for your program, you can use Qiskit to prepare inputs, such as circuits, observables (for Estimator), and customizable options to optimize your job. For more information, see the appropriate topic:

* `Getting started with Estimator <./tutorials/how-to-getting-started-with-estimator.ipynb>`__
* `Getting started with Sampler <./tutorials/how-to-getting-started-with-sampler.ipynb>`__
* :ref:`Migrate from qiskit-ibmq-provider to qiskit-ibm-runtime <migrate to primitives>`
