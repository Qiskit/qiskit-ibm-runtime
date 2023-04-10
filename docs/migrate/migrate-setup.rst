Migrate setup from ``qiskit-ibmq-provider``
==============================================

This guide describes how to migrate code from the legacy IBMQ provider (`qiskit-ibmq-provider`) package to use Qiskit Runtime (`qiskit-ibm-runtime`). This guide includes instructions to migrate legacy runtime programs to the new syntax. However, the ability to use custom uploaded programs is pending deprecation, so these should be migrated to use primitives instead.  

- For instructions to use Qiskit Runtime primitives, see the `migration guide <migrate-guide.html>`__.  
- For further details about migrating from `qiskit-ibmq-provider` to `qiskit-ibm-runtime`, see `Migration guide from qiskit-ibmq-provider <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/migrate_from_ibmq.html>`__.

 
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

.. code-block:: python

    # ibm cloud channel
    QiskitRuntimeService.save_account(channel="ibm_cloud", token="<IBM Cloud API key>", instance="<IBM Cloud CRN>", overwrite=True)

    # ibm quantum channel
    QiskitRuntimeService.save_account(channel="ibm_quantum", token="<IQX_TOKEN>", overwrite=True)

**Legacy - Load accounts**

.. code-block:: python

    IBMQ.load_account()

**Updated - Load accounts**

The new syntax combines the functionality from ``load_account()`` and ``get_provider()`` in one statement.

.. code-block:: python

    # to access saved credentials for ibm cloud channel
    service = QiskitRuntimeService(channel="ibm_cloud")

    # to access saved credentials for ibm quantum channel
    service = QiskitRuntimeService(channel="ibm_quantum")


Channel selection (get a provider)
------------------------------------------

Use the updated code to select a channel.

**Legacy**

.. code-block:: python

    provider = IBMQ.get_provider(project="my_project", group="my_group", hub="my_hub")

**Updated**

The new syntax combines the functionality from ``load_account()`` and ``get_provider()`` in one statement.
If using the ``ibm_quantum`` channel, the ``hub``, ``group``, and ``project`` are specified through the new
``instance`` keyword.

.. code-block:: python

    # to access saved credentials for ibm cloud channel
    service = QiskitRuntimeService(channel="ibm_cloud")

    # to access saved credentials for ibm quantum channel and select instance
    service = QiskitRuntimeService(channel="ibm_quantum", instance="my_hub/my_group/my_project")


Get the backend
------------------
Use the updated code to view backends.

**Legacy**

.. code-block:: python

    backend = provider.get_backend("ibmq_qasm_simulator")

**Updated**

.. code-block:: python

    backend = service.backend("ibmq_qasm_simulator")

Upload, view, or delete custom prototype programs
----------------------------------------------------
To work with custom programs, replace ``provider.runtime`` with ``service``.

.. note::
    This function is pending deprecation.

**Legacy**

.. code-block:: python

    # printing existing programs
    provider.runtime.pprint_programs()

    # deleting custom program
    provider.runtime.delete_program("my_program") # substitute "my_program" with your program id

    # uploading custom program
    program_id = provider.runtime.upload_program(
                data=program_data,
                metadata=program_json
                )

**Updated**

.. code-block:: python

    # printing existing programs
    service.pprint_programs()

    # deleting custom program
    service.delete_program("my_program") # substitute "my_program" with your program id

    # uploading custom program
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
