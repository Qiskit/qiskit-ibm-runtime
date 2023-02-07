#############################################
Migration guide from ``qiskit-ibmq-provider``
#############################################

Introduction
============

The classes related with Qiskit Runtime that used to be included in ``qiskit-ibmq-provider`` are now part of ``qiskit-ibm-runtime``. Before, the provider used to populate the ``qiskit.providers.ibmq.runtime`` namespace with objects for Qiskit Runtime that now live in the ``qiskit_ibm_runtime`` module.

Changes in Class name and location
==================================

The module from which the classes are imported changed. Below is a table of example access patterns in ``qiskit.providers.ibmq.runtime`` and the new form with ``qiskit_ibm_runtime``:

.. list-table:: Migrate from ``qiskit.providers.ibmq.runtime`` in ``qiskit-ibmq-provider`` to ``qiskit-ibm-runtime`` 
   :header-rows: 1

   * - class in ``qiskit-ibmq-provider``
     - class in ``qiskit-ibm-runtime``
     - Notes
   * - ``qiskit.providers.ibmq.runtime.IBMRuntimeService``
     - :class:`qiskit_ibm_runtime.QiskitRuntimeService`
     - ``IBMRuntimeService`` class was removed from ``qiskit_ibm_runtime 0.6.0`` and replaced by :class:`~QiskitRuntimeService`.
   * - ``qiskit.providers.ibmq.runtime.RuntimeJob``
     - :class:`qiskit_ibm_runtime.RuntimeJob`
     -  
   * - ``qiskit.providers.ibmq.runtime.RuntimeProgram``
     - :class:`qiskit_ibm_runtime.RuntimeProgram`
     - 
   * - ``qiskit.providers.ibmq.runtime.UserMessenger``
     - :class:`qiskit_ibm_runtime.program.UserMessenger`
     - Notice the new location, in ``qiskit_ibm_runtime.program``
   * - ``qiskit.providers.ibmq.runtime.ProgramBackend``
     - :class:`qiskit_ibm_runtime.program.ProgramBackend`
     - Notice the new location, in ``qiskit_ibm_runtime.program``
   * - ``qiskit.providers.ibmq.runtime.ResultDecoder``
     - :class:`qiskit_ibm_runtime.program.ResultDecoder`
     - Notice the new location, in ``qiskit_ibm_runtime.program``
   * - ``qiskit.providers.ibmq.runtime.RuntimeEncoder``
     - :class:`qiskit_ibm_runtime.RuntimeEncoder`
     - 
   * - ``qiskit.providers.ibmq.runtime.RuntimeDecoder``
     - :class:`qiskit_ibm_runtime.RuntimeDecoder`
     - 
   * - ``qiskit.providers.ibmq.runtime.ParameterNamespace``
     - :class:`qiskit_ibm_runtime.ParameterNamespace`
     - 
   * - ``qiskit.providers.ibmq.runtime.RuntimeOptions``
     - :class:`qiskit_ibm_runtime.RuntimeOptions`
     - 
     
