.. _limitations:

===================
Runtime limitations
===================

- **Currently in private beta**
   
   The Qiskit Runtime is currently in private beta testing with members of the
   IBM Quantum Network.  A general release will follow after this testing is
   completed. 

- **Limited quantum systems available for Qiskit Runtime**
   
   Currently only the *ibmq_montreal* and *ibmq_qasm_simulator* are accessible
   via the Qiskit runtime architecture.

- **Uploading custom quantum programs not supported**
   
   At present, uploading custom programs to the Qiskit Runtime is not supported.
   This will be relaxed in upcoming releases.

- **Five circuit limit per circuit runner job**

   The current Qiskit Runtime was designed for executing program scripts,   
   and is not tailored to large batches of quantum circuits.  As such, there
   is a size limitation that translates into roughly a five circuit maximum
   per job.

.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
