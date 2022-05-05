.. _how_to/specify_the_backend:

===================
Specify the backend
===================

This guide shows you how to specify the backend to run a runtime programs.

Before you begin
----------------

Throughout this guide, we will assume that you have setup the Qiskit Runtime service instance (see :doc:`../getting_started`) and initialize it as ``service``:

.. code-block::

    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService()

Specify the backend
-------------------

You can specify the backend to run a runtime program by specifying the ``backend_name`` option and pass to the program:

.. code-block::

    options = {"backend_name": "ibmq_qasm_simulator"}
    job = service.run(
        program_id="hello-world",
        options=options
    )

For IBM Quantum, specifying the backend is required.

For IBM Cloud, specifying the backend is optional. If you do not specify one, the job is sent to the least busy device that you have access to.