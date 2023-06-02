#########################################
Qiskit Runtime overview
#########################################

Overview
==============

Qiskit Runtime is a quantum computing service and programming model that streamlines quantum computations. It is designed to use classical compute resources to execute quantum circuits with more efficiency on quantum processors. It improves efficiency by giving you access to *primitives*, which are designed to run in *sessions*.

Primitives are a simplified interface for defining `near-time quantum-classical workloads <https://research.ibm.com/blog/near-real-time-quantum-compute>`_ required to efficiently build and customize applications. They are designed to be run in sessions, which essentially bind the backend to your session jobs for a period of time so they are not interrupted by other users’ jobs.

The following figure illustrates how the Qiskit Runtime program jobs are run when using sessions and primitives.  The first job waits through the regular fair-share queue.  When it starts to run, the session is started.  After the first session job is finished processing, the next job in the session is run.  This process continues until the session is paused (due to a lack of queued session jobs) or closed.

.. figure:: images/runtime-architecture.png
    :align: center

Key concepts
==============

**Primitives**

Primitives are core functions that provide a simplified interface for defining `near-time quantum-classical workloads <https://research.ibm.com/blog/near-real-time-quantum-compute>`_  required to efficiently build and customize applications. The initial release of Qiskit Runtime includes two primitives: Estimator and Sampler. They perform foundational quantum computing tasks and act as an entry point to the Qiskit Runtime service.


**Estimator**

The estimator primitive allows users to efficiently calculate and interpret expectation
values of quantum operators required for many algorithms. Users specify circuits that
prepare quantum states and then Pauli-basis observables to measure on those states. The
estimator can use advanced error mitigation capabilities to improve the accuracy of the
returned expectation values.

**Sampler**

This primitive takes a user circuit as input and returns a quasiprobability distribution
over the measurement outcomes. This generalizes histograms from quantum circuits to allow
for error mitigation of readout.

**Session**

A session is a contract between the user and the Qiskit Runtime service that ensures that a collection of jobs can be grouped and jointly prioritized by the quantum computer’s job scheduler. This eliminates artificial delays caused by other users’ jobs running on the same quantum device during the session time.



Next steps
=================================

`Getting started <getting_started.html>`_

`Tutorials <tutorials.html>`_

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Get started

    Overview <self>
    Getting Started <getting_started>
    backend.run vs. Qiskit Runtime <compare>
    Introduction to primitives <primitives>
    Introduction to sessions <sessions>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Tutorials

    Get started with Estimator <tutorials/how-to-getting-started-with-estimator>
    Get started with error suppression and error mitigation <tutorials/Error-Suppression-and-Error-Mitigation>
    VQE with Estimator <tutorials/vqe_with_estimator>
    CHSH with Estimator <tutorials/chsh_with_estimator>
    Get started with Sampler <tutorials/how-to-getting-started-with-sampler>
    QPE with Sampler <tutorials/qpe_with_sampler>
    Grover with Sampler <tutorials/grover_with_sampler>
    SEA with Sampler <tutorials/sea_with_sampler>
    QAOA with Sampler <tutorials/qaoa_with_sampler>
    Submit user-transpiled circuits using primitives <tutorials/user-transpiled-circuits>
    All tutorials <tutorials>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: How to

    Run a primitive in a session <how_to/run_session>
    Run on quantum backends <how_to/backends>
    Retrieve job results <how_to/retrieve_results>
    Configure primitive options <how_to/options>
    Configure error mitigation options <how_to/error-mitigation>
    Configure error suppression <how_to/error-suppression>
    Manage your account <how_to/account-management>
    Run noisy simulations <how_to/noisy_simulators>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Migrate

    Migrate to using Qiskit Runtime primitives <migrate/migrate-guide>
    Migrate your setup from qiskit-ibmq-provider <migrate/migrate-setup>
    Use Estimator to design an algorithm <migrate/migrate-estimator>
    Use Sampler to design an algorithm <migrate/migrate-sampler>
    Update parameter values while running <migrate/migrate-update-parm>
    Work with updated Qiskit algorithms <migrate/migrate-qiskit-alg>
    Algorithm tuning options (shots, transpilation, error mitigation) <migrate/migrate-tuning>


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

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Reference

    API Reference <apidocs/ibm-runtime>
    Swagger API for building applications that use Qiskit Runtime <https://us-east.quantum-computing.cloud.ibm.com/openapi/>
    API error codes <errors>
    FAQs <faqs>
    Retired systems <retired>
    Release Notes <release_notes>
    GitHub <https://github.com/Qiskit/qiskit-ibm-runtime>

.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
