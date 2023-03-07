How does backend.run differ from Qiskit Runtime primitives?
============================================================================

The existing Qiskit backend interface (``backend.run()``) was originally
designed to accept a list of circuits and return shot counts for every
job. As our users' needs changed, we realized that we would need a new,
more flexible tool to address those needs, and Qiskit Runtime was born.


Using Qiskit alone
------------------

Qiskit was originally designed to drive circuit execution directly.
Qiskit users submit circuits and receive results from the jobs that are
run on a quantum system. Often, these jobs are part of a larger
algorithm that includes an iterative (variational) approach to optimize
circuit parameters. In this sequence, queuing up each job results in
longer processing times.

Using Qiskit Runtime
--------------------

Qiskit Runtime offers advantages in workload performance. Variational
algorithms can run on classical compute resources that are colocated
with the QPUs through the Estimator primitive program. This allows users
to run iterative algorithm circuits back to back. In addition, sessions
can drive a sequence of jobs without having to re-queue each job,
avoiding latencies of queue wait times after the session is actively
running. As a result, Qiskit Runtime is much more efficient than its
predecessors.

+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Function                                                                        | backend.run           | Qiskit Runtime Primitives |
+=================================================================================+=======================+===========================+
| Primitive interface as abstraction for circuits and variational workload        | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Sessions to improve performance for a sequence of jobs                          | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Abstracted interface that allows for automated error suppression and mitigation | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Increased performance for variational algorithms                                | No                    | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Working examples of code developed by Qiskit community                          | Yes                   | No                        |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| OpenPulse                                                                       | Yes                   | No                        |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
| Pulse Gates                                                                     | Yes                   | Yes                       |
+---------------------------------------------------------------------------------+-----------------------+---------------------------+
