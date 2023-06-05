#########################################
Getting started
#########################################

Install Qiskit packages
========================

Install these packages. They let you create circuits and work with primitives
through Qiskit Runtime.

.. code-block:: bash

    pip install qiskit
    pip install qiskit-ibm-runtime


Find your access credentials
==============================

You can access Qiskit Runtime from either IBM Quantum or IBM Cloud.

**IBM Quantum**

`Retrieve your IBM Quantum token <https://quantum-computing.ibm.com/account>`_, and optionally save it for easy access later.

.. note::
    Account credentials are saved in plain text, so only do so if you are using a trusted device.

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService

    # Save an IBM Quantum account.
    QiskitRuntimeService.save_account(channel="ibm_quantum", token="MY_IBM_QUANTUM_TOKEN")



**IBM Cloud**

Retrieve your IBM Cloud access credentials, and optionally save it for easy access later.

* `Retrieve your IBM Cloud token <https://cloud.ibm.com/iam/apikeys>`__
* To retrieve your Cloud Resource Name (CRN), open the `Instances page <https://cloud.ibm.com/quantum/instances>`__ and click your instance. In the page that opens, click the icon to copy your CRN.

.. note::
    Account credentials are saved in plain text, so only do so if you are using a trusted device.

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService

    # Save an IBM Cloud account.
    QiskitRuntimeService.save_account(channel="ibm_cloud", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")


Test your setup
==============================

Run a simple circuit using `Sampler` to ensure that your environment is set up properly:

.. code-block:: python

    from qiskit.test.reference_circuits import ReferenceCircuits
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

    # You'll need to specify the credentials when initializing QiskitRuntimeService, if they are not previously saved.
    service = QiskitRuntimeService()
    backend = service.backend("ibmq_qasm_simulator")
    job = Sampler(backend).run(ReferenceCircuits.bell())
    print(f"job id: {job.job_id()}")
    result = job.result()
    print(result)


Getting started with primitives
=================================

.. nbgallery::

   tutorials/how-to-getting-started-with-sampler
   tutorials/how-to-getting-started-with-estimator


`See more tutorials <tutorials.html>`_
