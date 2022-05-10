#########################################
Qiskit Runtime overview
#########################################

Overview
==============

Qiskit Runtime is a quantum computing service and programming model that allows users to
optimize workloads and efficiently execute them on quantum systems at scale. The
programming model extends the existing interface in Qiskit with a set of new primitive
programs.

.. figure:: images/runtime-architecture.png
    :align: center


Key Concepts
==============

**Primitives**

Primitives are predefined programs that provide a simplified interface for defining
near-time quantum-classical workloads required to efficiently build and customize
applications. The initial release of Qiskit Runtime includes two primitives: Estimator
and Sampler. They perform foundational quantum computing tasks and act as an entry point
to the Qiskit Runtime service.


**Sampler**

This is a program that takes a user circuit as an input and generates an error-mitigated
readout of quasiprobabilities. This provides users a way to better evaluate shot results
using error mitigation and enables them to more efficiently evaluate the possibility of
multiple relevant data points in the context of destructive interference.


**Estimator**

The estimator primitive allows users to efficiently calculate and interpret expectation
values of quantum operators required for many algorithms. Users specify a list of circuits
and observables, then tell the program how to selectively group between the lists to
efficiently evaluate expectation values and variances for a given parameter input.


Next Steps
=================================

`Getting started <getting_started.html>`_

`Tutorials <tutorials.html>`_

.. toctree::
    :hidden:

    Overview <self>
    Getting Started <getting_started>
    Tutorials <tutorials>
    How to (rst) <how_to_rst>
    How to (md) <how_to_md>
    How to (ipynb) <how_to_ipynb>
    API Reference <apidocs/ibm-runtime>
    FAQs <faqs>
    Release Notes <release_notes>
    GitHub <https://github.com/Qiskit/qiskit-ibm-runtime>



.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
