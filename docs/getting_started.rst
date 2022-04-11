#########################################
Getting started
#########################################

Install Qiskit packages
========================

Install these packages. They let you create circuits and work with primitive programs 
via Qiskit Runtime.

.. code-block:: bash

    pip install qiskit
    pip install qiskit-ibm-runtime


Find your access credentials
==============================

You can access Qiskit Runtime from either IBM Quantum or IBM Cloud.

**IBM Quantum**

.. code-block:: python

    from qiskit_ibm_runtime import IBMRuntimeService

    # Save an IBM Quantum account.
    IBMRuntimeService.save_account(channel="ibm_quantum", token="MY_IBM_QUANTUM_TOKEN")

`Retrieve IBM Quantum token <https://quantum-computing.ibm.com/account>`_


**IBM Cloud**

.. code-block:: python

    from qiskit_ibm_runtime import IBMRuntimeService

    # Save an IBM Cloud account.
    IBMRuntimeService.save_account(channel="ibm_cloud", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")

`Retrieve IBM Cloud token <https://cloud.ibm.com/docs/quantum-computing?topic=quantum-computing-quickstart>`_


Test your setup
==============================

Run the Hello World program to ensure that your environment is set up properly:

.. code-block:: python

    from qiskit.test.reference_circuits import ReferenceCircuits
    from qiskit_ibm_runtime import IBMRuntimeService

    service = IBMRuntimeService()
    program_inputs = {'iterations': 1}
    options = {"backend_name": "ibmq_qasm_simulator"}
    job = service.run(program_id="hello-world",
                    options=options,
                    inputs=program_inputs
                    )
    print(f"job id: {job.job_id}")
    result = job.result()
    print(result)


Getting started with Primitives
=================================

.. nbgallery::

   tutorials/how-to-getting-started-with-sampler
   tutorials/how-to-getting-started-with-estimator


`See more tutorials <tutorials.html>`_