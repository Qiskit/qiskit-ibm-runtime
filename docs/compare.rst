How does Qiskit differ from Qiskit Runtime?
===========================================

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
can drive a sequence of jobs without having to requeue each job,
avoiding latencies of queue wait times after the session is actively
running. As a result, Qiskit Runtime is much more efficient than its
predecessors.

.. table:: Comparison of Qiskit to Qiskit Runtime

   +-----------------------+------------+----------------+
   | Function              | Qiskit     | Qiskit Runtime |
   +=======================+============+================+
   | Primitive interface   | No         | Yes            |
   | as abstraction for    |            |                |
   | circuits and          |            |                |
   | variational workload  |            |                |
   +-----------------------+------------+----------------+
   | Sessions to improve   | No         | Yes            |
   | performance for a     |            |                |
   | sequence of jobs      |            |                |
   +-----------------------+------------+----------------+
   | Abstracted interface  | No         | Yes            |
   | that allows for       |            |                |
   | automated error       |            |                |
   | suppression and       |            |                |
   | mitigation            |            |                |
   +-----------------------+------------+----------------+
   | Increased performance | No         | Yes            |
   | for variational       |            |                |
   | algorithms            |            |                |
   +-----------------------+------------+----------------+
   | Working examples of   | Yes        | No             |
   | code developed by     |            |                |
   | Qiskit community      |            |                |
   +-----------------------+------------+----------------+
   | OpenPulse             | Yes        | No             |
   +-----------------------+------------+----------------+
