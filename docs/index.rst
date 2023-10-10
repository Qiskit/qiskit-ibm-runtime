#########################################
Qiskit Runtime 0.12.2 documentation
#########################################

Overview
==============

Qiskit Runtime is a cloud-based quantum computing service developed by IBM. It offers computational *primitives* to perform foundational quantum computing tasks that use built-in error suppression and mitigation techniques. Primitives can be executed inside of *sessions*, allowing collections of circuits to be jointly run on a quantum computer without being interrupted by other users’ jobs. The combination of primitives, error suppression / mitigation, and sessions paves the way to efficiently build and execute scalable quantum applications.

The following figure illustrates how one can use Qiskit Runtime sessions and primitives. The first session request (job) waits through the regular `fair-share queue <https://quantum-computing.ibm.com/admin/docs/admin/manage/systems/queue>`__. When it starts to run, the session is started. After the first session job is finished processing, the next job in the session is run. This process continues until the session is paused (due to a lack of queued session jobs) or closed.

.. figure:: images/runtime-architecture.png
    :align: center

Key concepts
==============

**Primitives**

Primitives are base level operations that serve as building blocks for many quantum algorithms and applications. Through these primitives, users can obtain high-fidelity results, without needing detailed hardware knowledge.  This abstraction allows you to write code, using Qiskit algorithms or otherwise, that can run on different quantum hardware or simulators without having to explicitly manage aspects such as compilation, optimization, and error suppression / mitigation. The primitives offered by :mod:`qiskit_ibm_runtime` add additional options specific to IBM services. See `Introduction to primitives <primitives.html>`__ for further details.

There are currently two primitives defined in Qiskit: Estimator and Sampler.


**Estimator**

The estimator primitive allows you to efficiently calculate and interpret expectation values of quantum operators; the values of interest for many near-term quantum algorithms. You specify circuits that prepare quantum states and then Pauli-basis observables to measure on those states. The estimator can use advanced error suppression and mitigation capabilities to improve the accuracy of the returned expectation values.

**Sampler**

This primitive takes circuits as input and returns a quasi-probability distribution over the measurement outcomes. This generalizes histograms from quantum circuits, allowing for mitigation of readout errors.

**Error suppression / mitigation**

While building a fault-tolerant quantum computation is the ultimate goal, at present, calculations performed on near-term quantum computers are susceptible to noise.  Qiskit Runtime offers several methods for preventing errors before they occur (error suppression techniques) and dealing with those that do occur (error mitigation techniques).  

**Session**

A session allows a collection of jobs to be grouped and jointly scheduled by the Qiskit Runtime service, facilitating iterative use of quantum computers without incurring queuing delays on each iteration. This eliminates artificial delays caused by other users’ jobs running on the same quantum device during the session. See `Introduction to sessions <sessions.html>`__ for further details.



Next steps
=================================

`Getting started <getting_started.html>`_

`Tutorials <tutorials.html>`_

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Get started

    Overview <self>
    Getting started <getting_started>
    backend.run vs. Qiskit Runtime <compare>
    Introduction to primitives <primitives>
    Introduction to sessions <sessions>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Tutorials

    Get started with Estimator <tutorials/how-to-getting-started-with-estimator>
    Get started with Sampler <tutorials/how-to-getting-started-with-sampler>
    Get started with error suppression and error mitigation <tutorials/Error-Suppression-and-Error-Mitigation>
    CHSH with Estimator <tutorials/chsh_with_estimator>
    VQE with Estimator <tutorials/vqe_with_estimator>
    Grover with Sampler <tutorials/grover_with_sampler>
    QAOA with Primitives <tutorials/qaoa_with_primitives>
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
