#########################################
Qiskit Runtime overview
#########################################

Overview
==============

Qiskit Runtime is a cloud-based quantum computing service developed by IBM. It offers computational *primitives* to perform foundational quantum computing tasks and has built-in error suppression and mitigation. In addition, Qiskit Runtime has *sessions*, which allow you to run your circuits on a quantum computer without being interrupted by other users’ jobs. The combination of primitives, error suppression / mitigation, and sessions paves the way to efficiently build and execute scalable quantum applications.

The following figure illustrates how one can use Qiskit Runtime sessions and primitives. The first session request (job) waits through the regular fair-share queue. When it starts to run, the session is started. After the first session job is finished processing, the next job in the session is run. This process continues until the session is paused (due to a lack of queued session jobs) or closed.

.. figure:: images/runtime-architecture.png
    :align: center

Key concepts
==============

**Primitives**

Primitives are base level operations that serve as building blocks for many quantum algorithms and applications. The `base primitive interfaces <https://qiskit.org/documentation/apidoc/primitives.html>`__ are defined in Qiskit Terra, and many Qiskit algorithms use the primitives natively. This abstraction allows you to write the same code, using Qiskit algorithms or otherwise, that can run on different quantum hardware or simulators without having to explicitly manage some of the finer details. The primitves offered by `qiskit_ibm_runtime <https://qiskit.org/ecosystem/ibm-runtime/apidocs/ibm-runtime.html>`__ add additional options specific to IBM's service. See `Introduction to primitives <primitives.html>`__ for further details.

There are currently two primitives defined in Qiskit: Estimator and Sampler.


**Estimator**

The estimator primitive allows you to efficiently calculate and interpret expectation values of quantum operators required for many algorithms. You specify circuits that prepare quantum states and then Pauli-basis observables to measure on those states. The estimator can use advanced error mitigation capabilities to improve the accuracy of the returned expectation values.

**Sampler**

This primitive takes circuits as input and returns a quasi-probability distribution over the measurement outcomes. This generalizes histograms from quantum circuits to allow for error mitigation of readout.

**Error suppression / mitigation**

Errors occur naturally in a computer, and building fault-tolerant quantum computation is our ultimate goal. While we continue to research how to build error-corrected qubits at scale, Qiskit Runtime offers a number of error suppression and mitigation techniques that alleviate the effect of noise.

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
    Get started with error suppression and error mitigation <tutorials/Error-Suppression-and-Error-Mitigation>
    VQE with Estimator <tutorials/vqe_with_estimator>
    CHSH with Estimator <tutorials/chsh_with_estimator>
    Get started with Sampler <tutorials/how-to-getting-started-with-sampler>
    QPE with Sampler <tutorials/qpe_with_sampler>
    Grover with Sampler <tutorials/grover_with_sampler>
    SEA with Sampler <tutorials/sea_with_sampler>
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
