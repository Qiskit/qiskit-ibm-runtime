.. _max_execution_time:

======================
Maximum Execution Time
======================

To ensure fairness, there is a maximum execution time for each Qiskit Runtime job. If
a job exceeds this time limit, it is forcibly cancelled. This is represented in the job
status as `Canceled - Ran too long`. The maximum execution time is the
smaller of 1) the system limit and 2) the ``max_execution_time`` defined by the program.
The system limit is defined below:

Qiskit Runtime on IBM Cloud
---------------------------

The system limit on the job execution time is 3 hours for a job running on a simulator
and 8 hours for a job running on a physical system.

Qiskit Runtime on IBM Quantum (legacy)
--------------------------------------

The system limit on the job execution time is

+------------------+--------------+-----------+--------------+-----------+
|                  | Public Program           | Private Program          |
+==================+==============+===========+==============+===========+
|                  | Premium User | Open User | Premium User | Open User |
+------------------+--------------+-----------+--------------+-----------+
| Simulated Device | 3h           | 1h        | 3h           |1h         |
+------------------+--------------+-----------+--------------+-----------+
| Real Device      | 8h           | 4h        | 8h           |2h         |
+------------------+--------------+-----------+--------------+-----------+

Note that a *premium user* here means a user who has access to backends in providers other than ibm-q/open/main.

=================
Other Limitations
=================

- Programs cannot exceed 750KB in size.
- Inputs to jobs cannot exceed 64MB in size.

.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
