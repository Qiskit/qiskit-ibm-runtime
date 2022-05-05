.. _how_to/list_available_backends:

=======================
List available backends
=======================

This guide shows you how to list all the backends available to you.

Before you begin
----------------

Throughout this guide, we will assume that you have setup the Qiskit Runtime service instance (see :doc:`../getting_started`) and initialize it as ``service``:

.. code-block::

    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService()


List available backends
-----------------------

You can see the list of available backends by calling ``QiskitRuntimeService.backends()`` :

.. code-block::

    service.backends()

