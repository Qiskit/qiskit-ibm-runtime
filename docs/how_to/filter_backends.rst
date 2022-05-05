.. _how_to/filter_backends:

===============
Filter backends
===============

This guide shows you how to apply filters for selecting backends.

Before you begin
----------------

Throughout this guide, we will assume that you have setup the Qiskit Runtime service instance (see :doc:`../getting_started`) and initialize it as ``service``:

.. code-block::

    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService()


You can apply filters for choosing backends including the following options. See `the API reference <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.QiskitRuntimeService.backends.html#qiskit_ibm_runtime.QiskitRuntimeService.backends>`_ for more details.

Filter by backend name
----------------------

You can choose a backend by specifying the backend name. Here is an example to get the ``ibmq_qasm_simulator`` backend:

.. code-block::

    service.backends(name='ibmq_qasm_simulator')


Filter by minimum number of qubits
----------------------------------

You can filter backends by specifying the minimum number of qubits. Here is an example to get backends that has at least 20 qubits:

.. code-block::

    service.backends(min_num_qubits=20)


Filter by IBM Quantum provider
------------------------------

If you are accessing Qiskit Runtime service from IBM Quantum platform, you can filter backends using the ``hub/group/project`` format of IBM Quantum provider. See `IBM Quantum account page <https://quantum-computing.ibm.com/account>`_ for the list of providers you have access to. Here is an example to get backends that are availabe to the default IBM Quantum open provider:

.. code-block::

    service.backends(instance='ibm-q/open/main')


Filter by backend configuration or status
-----------------------------------------

You can specify ``True`` / ``False`` criteria in the backend configuration or status using optional keyword arguments ``**kwargs``. Here is an example to get the operational real backends:

.. code-block::

    service.backends(simulator=False, operational=True)


Filter by complex filters
-------------------------

You can also apply more complex filters such as lambda functions. Here is an example to get backends that has quantum volume larger than 16:

.. code-block::

    service.backends(
        simulator=False,
        filters=lambda b: b.configuration().quantum_volume > 16)

