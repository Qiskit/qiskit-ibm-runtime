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

IBM Quantum
------------------

.. code-block:: python

    from qiskit_ibm_runtime import IBMRuntimeService
    # Save your credentials on disk.# IBMRuntimeService.save_account(auth="legacy", token=<IBM Quantum API key>)
    service = IBMRuntimeService()

`Retrieve token </>`_


IBM Cloud
------------------

.. code-block:: python

    from qiskit_ibm_runtime import IBMRuntimeService 
    # Save account to disk. IBMRuntimeService.save_account(auth="cloud", token=<IBM Cloud API key>, instance=<IBM Cloud CRN or Service instance name>) service = IBMRuntimeService()
    Authenticate to the service

`Retrieve token </>`_


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

`Getting started with Sampler </>`_

`Getting started with Estimator </>`_