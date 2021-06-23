.. _limitations:

===================
Runtime limitations
===================

- **Currently in private beta**

   The Qiskit Runtime is currently in private beta testing with premium users.
   A general release will follow after this testing is completed.

- **Limited quantum systems available for Qiskit Runtime**
   
   Not all systems and simulators support Qiskit Runtime.
   A backend supports Qiskit Runtime if it has ``runtime`` in the ``input_allowed``
   configuration attribute::

      backend = provider.backend.ibmq_montreal
      support_runtime = 'runtime' in backend.configuration().input_allowed
      print(f"Does {backend.name()} support Qiskit Runtime? {support_runtime}")

   You can also use ``input_allowed`` as a filter in ``backends()``
   (requires Qiskit 0.27.0 or later)::

      # Get a list of all backends that support runtime.
      runtime_backends = provider.backends(input_allowed='runtime')
      print(f"Backends that support Qiskit Runtime: {runtime_backends}")

- **Uploading custom quantum programs not supported**
   
   At present, uploading custom programs to the Qiskit Runtime is not supported.
   This will be relaxed in upcoming releases.


.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
