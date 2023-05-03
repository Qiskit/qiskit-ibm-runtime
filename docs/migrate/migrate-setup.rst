Migrate setup from ``qiskit-ibmq-provider``
==============================================

This guide describes how to migrate code from the legacy IBMQ provider (`qiskit-ibmq-provider`) package to use Qiskit Runtime (`qiskit-ibm-runtime`). This guide includes instructions to migrate legacy runtime programs to the new syntax. However, the ability to use custom uploaded programs is pending deprecation, so these should be migrated to use primitives instead.  
 
Import path
-------------

The import path has changed as follows:

**Legacy**

.. code-block:: python

    from qiskit import IBMQ

**Updated**

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService

Save and load accounts
------------------------------------

Use the updated code to work with accounts.

**Legacy - Save accounts**

.. code-block:: python

    IBMQ.save_account("<IQX_TOKEN>", overwrite=True)

**Updated - Save accounts**
The new syntax accepts credentials for Qiskit Runtime m on IBM Cloud or IBM Quantum Platform. For more information on retrieving account credentials, see the `getting started guide <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/getting_started.html>`_.
.. code-block:: python

    # IBM cloud channel
    QiskitRuntimeService.save_account(channel="ibm_cloud", token="<IBM Cloud API key>", instance="<IBM Cloud CRN>", overwrite=True)

    # IBM quantum channel
    QiskitRuntimeService.save_account(channel="ibm_quantum", token="<IQP_TOKEN>", overwrite=True)

**Updated - Name saved credentials**
You can now name your saved credentials and load the credentials by name.  Example:
.. code-block:: python

    # Save different accounts for open and premium access

    QiskitRuntimeService.save_account(channel="ibm_quantum", token="<IQX_TOKEN>", instance="h1/g1/p1", name="premium")
    QiskitRuntimeService.save_account(channel="ibm_quantum", token="<IQX_TOKEN>", instance="h2/g2/p2", name="open")

    # Load the "open" credentials 

    service = QiskitRuntimeService(name="open")

**Legacy - Load accounts**

.. code-block:: python

    IBMQ.load_account()

**Updated - Load accounts**

The new syntax combines the functionality from ``load_account()`` and ``get_provider()`` in one statement. The ``channel`` input parameter is optional. If multiple accounts have been saved in one device and no ``channel`` is provided, the default is ``"ibm_cloud"``.

.. code-block:: python

    # To access saved credentials for the IBM cloud channel
    service = QiskitRuntimeService(channel="ibm_cloud")

    # To access saved credentials for the IBM quantum channel
    service = QiskitRuntimeService(channel="ibm_quantum")


Channel selection (get a provider)
------------------------------------------

Use the updated code to select a channel.

**Legacy**

.. code-block:: python

    provider = IBMQ.get_provider(project="my_project", group="my_group", hub="my_hub")

**Updated**

The new syntax combines the functionality from ``load_account()`` and ``get_provider()`` in one statement.
When using the ``ibm_quantum`` channel, the ``hub``, ``group``, and ``project`` are specified through the new
``instance`` keyword.

.. code-block:: python

    # To access saved credentials for the IBM cloud channel
    service = QiskitRuntimeService(channel="ibm_cloud")

    # To access saved credentials for the IBM quantum channel and select an instance
    service = QiskitRuntimeService(channel="ibm_quantum", instance="my_hub/my_group/my_project")


Get the backend
------------------
Use the updated code to view backends.

**Legacy**

.. code-block:: python

    backend = provider.get_backend("ibmq_qasm_simulator")

**Updated**

.. code-block:: python

    # method 1: Initialize a new service:
    backend = service.backend("ibmq_qasm_simulator")

    # method 2: Specify an instance in service.backend() 
    QiskitRuntimeService.backend(name=ibmq_qasm_simulator, instance=None)

Upload, view, or delete custom prototype programs
----------------------------------------------------
To work with custom programs, replace ``provider.runtime`` with ``service``.

.. note::
    This function is pending deprecation.

**Legacy**

.. code-block:: python

    # Printing existing programs
    provider.runtime.pprint_programs()

    # Deleting custom program
    provider.runtime.delete_program("my_program") # Substitute "my_program" with your program ID

    # Uploading custom program
    program_id = provider.runtime.upload_program(
                data=program_data,
                metadata=program_json
                )

**Updated**

.. code-block:: python

    # Printing existing programs
    service.pprint_programs()

    # Deleting custom program
    service.delete_program("my_program") # Substitute "my_program" with your program ID

    # Uploading custom program
    program_id = service.upload_program(
                data=program_data,
                metadata=program_json
                )

Run prototype programs
---------------------------

To run prototype programs, replace ``provider.runtime`` with ``service``.

.. note::
    This function is pending deprecation.

**Legacy**

.. code-block:: python

    program_inputs = {"iterations": 3}
    options = {"backend_name": backend.name()}
    job = provider.runtime.run(program_id="hello-world",
                               options=options,
                               inputs=program_inputs
                              )
    print(f"job id: {job.job_id()}")
    result = job.result()
    print(result)

**Updated**

.. code-block:: python

    program_inputs = {"iterations": 3}
    options = {"backend": ""}
    job = service.run(program_id="hello-world",
                      options=options,
                      inputs=program_inputs
                      )
    print(f"job id: {job.job_id()}")
    result = job.result()
    print(result)
