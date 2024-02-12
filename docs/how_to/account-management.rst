Manage your account
=================================

Qiskit Runtime is available on both IBM Cloud and IBM Quantum Platform. The former requires an IBM Cloud account and the latter requires an IBM Quantum account. If you don't have the necessary account, refer to the appropriate link:

* `Setting up your IBM Cloud account <https://cloud.ibm.com/docs/account?topic=account-account-getting-started>`__
* `Access your IBM Quantum account <https://quantum-computing.ibm.com/account>`__

There are several methods for account management. Your account credentials can be saved to disk or used in a session and never saved.

* `save_account()`: Save your account to disk for future use.
* `delete_account()`: Delete the saved account from disk.
* `active_account()`: List the account currently in the session.
* `saved_account()`: List the account stored on disk.

Store credentials
-----------------

The ``save_account()`` method can be used to store your account credentials on disk, in the ``$HOME/.qiskit/qiskit-ibm.json`` file. After the credentials are saved, you will only need to use ``QiskitRuntimeService()`` to initialize your account in the future.

.. note::
  Account credentials are saved in plain text, so only do so if you are using a trusted device.

Following are examples of saving an IBM Cloud and an IBM Quantum account. The ``channel`` parameter allows to distinguish between different account types. If you are saving multiple accounts per channel, consider using the ``name`` parameter to differentiate them.

.. code-block:: python

  from qiskit_ibm_runtime import QiskitRuntimeService

  # Save an IBM Cloud account on disk.
  QiskitRuntimeService.save_account(channel="ibm_cloud", token=<*IBM Cloud API key*>, instance=<*IBM Cloud CRN*> or <*IBM Cloud service name*>)

  # Save an IBM Quantum account on disk.
  QiskitRuntimeService.save_account(channel="ibm_quantum", token=<*IBM Quantum API token*>)

Initialize your account
-------------------------

You need to initialize your account in a Python session before you can start using Qiskit Runtime. If you have the credentials already saved, you can initialize an ``QiskitRuntimeService`` instance without additional parameters.

.. code-block:: python

  # Read default credentials from disk.
  service = QiskitRuntimeService()

If you have both an IBM Cloud and an IBM Quantum accounts saved, ``QiskitRuntimeService()`` loads the IBM Cloud account by default. To load the IBM Quantum account instead, specify ``QiskitRuntimeService(channel="ibm_quantum")``.

Alternatively, if you specified a name for your account when saving it, you can also specify the name of the account to load.

.. code-block:: python

  # Save an IBM Cloud account on disk and give it a name.
  QiskitRuntimeService.save_account(channel="ibm_cloud", token=<*IBM Cloud API key*>, instance=<*IBM Cloud CRN*>, name="prod")

  service = QiskitRuntimeService(name="prod")

If you want to use your credentials for just the session rather than saving it, you can pass the credentials in when initializing the ``QiskitRuntimeService`` instance:

.. code-block:: python

  # Initialize an IBM Cloud account without saving it.
  service = QiskitRuntimeService(channel="ibm_cloud", token=<*IBM Cloud API key*>, instance=<*IBM Cloud CRN*>)
