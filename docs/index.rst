#########################################
Qiskit Runtime overview
#########################################

Overview
==============

Qiskit Runtime is a quantum computing service and programming model that allows users to optimize 
workloads and efficiently execute them on quantum systems at scale. The programming model introduces 
a set of interfaces, in the form of primitive programs.

.. figure:: images/runtime_arch.png
    :align: center


Key Concepts
==============

Runtimes
------------------

Primitives are predefined programs that provide a simplified interface for building and customization 
applications. The initial release of Qiskit Runtime includes two primitives: Estimator and Sampler. 
They perform foundational quantum computing tasks and act as an entry point to the Qiskit Runtime service.


Primitives
------------------

The estimator primitive allows users to efficiently calculate and interpret expectation values of 
quantum operators required for many algorithms. Users specify a list of circuits and observables, 
then tell the program how to selectively group between the lists to efficiently evaluate expectation 
values and variances for a given parameter input.

Sampler
------------------
The sampler primitive allows users to more accurately contextualize counts. It takes a user circuit 
as an input and generates an error-mitigated readout of quasiprobabilities. This enables users to 
more efficiently evaluate the possibility of multiple relevant data points in the context of 
destructive interference.

`Learn more <https://cloud.ibm.com/docs/quantum-computing?topic=quantum-computing-overview>`_


Next Steps
=================================

`Getting started <getting_started.html>`_

`How to guides <how_tos.html>`_

.. toctree::
    :hidden:

    Overview <self>
    Getting Started <getting_started>
    How to <how_tos>
    Explanation <explanations>
    Tutorials <tutorials>
    API Reference <apidocs/ibm-runtime>
    FAQs <faqs>
    Release Notes <release_notes>
    GitHub <https://github.com/Qiskit/qiskit-ibm-runtime>



.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
