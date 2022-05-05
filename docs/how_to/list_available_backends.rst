.. _how_to/list_available_backends:

=======================
List available backends
=======================

This guide shows you how to specify the backend and how to see the list of available backends (physical quantum systems or simulators) and apply filters to choose a backend to run a runtime programs.

Before you begin
----------------

Throughout this guide, we will assume that you have `setup the Qiskit Runtime service instance <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/getting_started.html>`_ and initialize it as ``service``:

.. code-block::

    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService()


List available backends
-----------------------

You can see the list of available backends by calling ``QiskitRuntimeService.backends()`` :

.. code-block::

    service.backends()

