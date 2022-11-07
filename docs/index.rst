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
   :maxdepth: 1
   :hidden:
   :caption: Get started

    Overview <self>
    Getting Started <getting_started>
    Qiskit vs. Qiskit Runtime <compare>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Tutorials

    Getting started with Estimator <tutorials/how-to-getting-started-with-estimator>
    CHSH with Estimator <tutorials/chsh_with_estimator>
    VQE with Estimator <tutorials/vqe_with_estimator>
    Getting started with Sampler <tutorials/how-to-getting-started-with-sampler>
    QPE with Sampler <tutorials/qpe_with_sampler>
    Grover with Sampler <tutorials/grover_with_sampler>
    SEA with Sampler <tutorials/sea_with_sampler>
    All tutorials <tutorials>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: How to

    Work with primitives <how_to/primitives>
    Work with sessions <how_to/sessions>
    Configure primitive options <how_to/options>
    Configure error mitigation options <how_to/resiliance>
    Configure optimization levels <how_to/optimization>
    Configure transpilation settings <how_to/transpilation>
    Run a primitive program in a session <how_to/run_session>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Migrate to using primitives

    Why migrate? <how_to/migrate-overview>
    Migrate code <how_to/migrate-code>
    Considerations <how_to/migrate-FAQ>
    Use Sampler in an algorithm <how_to/migrate-sampler>
    Use Estimator in an algorithm <how_to/migrate-estimator>
    Use Estimator and Sampler in an algorithm <how_to/migrate-est-sam>
    Update parameter values while running <how_to/migrate-update-parm>
    Primitive-based routines <how_to/migrate-prim-based>
    End-to-end example <how_to/migrate-e2e>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Work with Qiskit Runtime in IBM Cloud

    Getting started <cloud/quickstart>
    Pricing plans <cloud/plans>
    Plan for an organization <cloud/quickstart-org>
    Configure for an organization <cloud/quickstart-steps-org>
    Manage users in an organization <cloud/cloud-provider-org>
    Manage the cost <cloud/cost>
    Set up Terraform <cloud/setup-terraform>
    Architecture and workload isolation <cloud/architecture-workload-isolation>
    Securing your data <cloud/data-security>
    Audit events <cloud/at-events>
    Release notes <cloud/release-notes>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Reference

    API Reference <apidocs/ibm-runtime>
    Swagger API for building applications that use Qiskit Runtime <https://us-east.quantum-computing.cloud.ibm.com/openapi/>
    FAQs <faqs>
    Release Notes <release_notes>
    GitHub <https://github.com/Qiskit/qiskit-ibm-runtime>

.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
