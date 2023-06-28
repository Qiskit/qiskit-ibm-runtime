How do Qiskit Runtime primitives differ from backend.run?
=========================================================

There are two methods for accessing IBM Quantum systems.  First, the
`qiskit-ibm-provider` package provides the ``backend.run()`` interface,
allowing direct access to IBM Quantum systems with no pre- or post-processing
involved.  This level of access is suitable for those users who want precise
control over circuit execution and result processing.  This level of access
is needed for those looking to work at the level Kernel developer developing,
for example, circuit optimization routines, error mitigation techniques, or
characterizing quantum systems.

In contrast, the Qiskit Runtime is designed to streamline the construction
of algorithms and applications by removing the need for users to understand
technical hardware and low-level software details.  Advanced processing techniques
for error suppression and mitigation are automtically applied, giving users
high-fidelity results without the burdeen of haivng to code these routines
themselves.  The inclusion of Sessions within the Qiskit runtime allows users
to run iterative algorithm circuits back to back, or batch collections of circuits,
without having to re-queue each job.  This results in more efficient utilization
of the qunatum processor, and reduces the total amount of time users spend running
complex computations.


+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Function                                                                        | backend.run           | Qiskit Runtime Primitives |
+=================================================================================+=======================+===========================+
| Abstracted interface for circuits and variational workloads                     | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Sessions to improve performance for a sequence of jobs                          | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Automated application of error suppression and mitigation techniques            | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Increased performance for variational algorithms                                | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Pulse Gates                                                                     | Yes                   | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Dynamic circuits                                                                | Yes                   | No                        |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
