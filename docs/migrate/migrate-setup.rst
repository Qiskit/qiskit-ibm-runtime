Migrate setup from ``qiskit-ibmq-provider``
==============================================

This guide describes how to migrate code from the legacy IBMQ provider (`qiskit-ibmq-provider`) package to use Qiskit Runtime (`qiskit-ibm-runtime`). This guide includes instructions to migrate legacy runtime programs to the new syntax. However, the ability to use custom uploaded programs is pending deprecation, so these should be migrated to use primitives instead.  

Changes in Class name and location
-----------------------------------

The classes related to Qiskit Runtime that used to be included in ``qiskit-ibmq-provider`` are now part of ``qiskit-ibm-runtime``. Before, the provider used to populate the ``qiskit.providers.ibmq.runtime`` namespace with objects for Qiskit Runtime. These now live in the ``qiskit_ibm_runtime`` module.

The module from which the classes are imported has changed. The following table contains example access patterns in ``qiskit.providers.ibmq.runtime`` and their new form in ``qiskit_ibm_runtime``:

..
   I had to take the :class: formatting out of the following table because it was too wide for the page and was writing on top of the right-hand navigation menu when everything was in tags.  When I took off one tag, sphinx put it in a scrollable table that didn't overrun the right-hand navigation, so I took them all out for consistency


.. list-table:: Migrate from ``qiskit.providers.ibmq.runtime`` in ``qiskit-ibmq-provider`` to ``qiskit-ibm-runtime`` 
   :header-rows: 1

   * - class in ``qiskit-ibmq-provider``
     - class in ``qiskit-ibm-runtime``
     - Notes
   * - ``qiskit.providers.ibmq.runtime.IBMRuntimeService``
     - ``qiskit_ibm_runtime.QiskitRuntimeService```
     - ``IBMRuntimeService`` class was removed from ``qiskit-ibm-runtime`` 0.6 and replaced by the new class in ``qiskit-ibm-runtime``.
   * - ``qiskit.providers.ibmq.runtime.RuntimeJob``
     - ``qiskit_ibm_runtime.RuntimeJob``
     -  
   * - ``qiskit.providers.ibmq.runtime.RuntimeProgram``
     - ``qiskit_ibm_runtime.RuntimeProgram``
     - 
   * - ``qiskit.providers.ibmq.runtime.UserMessenger``
     - ``qiskit_ibm_runtime.program.UserMessenger``
     - Notice the new location, in ``qiskit_ibm_runtime.program``
   * - ``qiskit.providers.ibmq.runtime.ProgramBackend``
     - ``qiskit_ibm_runtime.program.ProgramBackend``
     - Notice the new location, in ``qiskit_ibm_runtime.program``
   * - ``qiskit.providers.ibmq.runtime.ResultDecoder``
     - ``qiskit_ibm_runtime.program.ResultDecoder``
     - Notice the new location, in ``qiskit_ibm_runtime.program``
   * - ``qiskit.providers.ibmq.runtime.RuntimeEncoder``
     - ``qiskit_ibm_runtime.RuntimeEncoder``
     - 
   * - ``qiskit.providers.ibmq.runtime.RuntimeDecoder``
     - ``qiskit_ibm_runtime.RuntimeDecoder``
     - 
   * - ``qiskit.providers.ibmq.runtime.ParameterNamespace``
     - ``qiskit_ibm_runtime.ParameterNamespace``
     - 
   * - ``qiskit.providers.ibmq.runtime.RuntimeOptions``
     - ``qiskit_ibm_runtime.RuntimeOptions``
     - 

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
The new syntax accepts credentials for Qiskit Runtime on IBM Cloud or IBM Quantum Platform. For more information on retrieving account credentials, see the `getting started guide <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/getting_started.html>`_.

.. code-block:: python

    # IBM cloud channel
    QiskitRuntimeService.save_account(channel="ibm_cloud", token="<IBM Cloud API key>", instance="<IBM Cloud CRN>", overwrite=True)

    # IBM quantum channel
    QiskitRuntimeService.save_account(channel="ibm_quantum", token="<IQP_TOKEN>", overwrite=True)

**Updated - Name saved credentials**
You can now name your saved credentials and load the credentials by name.  

**Example:**

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

    provider = IBMQ.get_provider(hub="h1", group="g1", project="p1")
    backend = provider.get_backend("ibm_backend")

**Updated**

.. code-block:: python

    # You can specify the instance in service.backend() instead of initializing a new service
    backend = service.backend("ibm_backend", instance="h1/g1/p1")
