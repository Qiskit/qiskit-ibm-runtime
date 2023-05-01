.. _faqs/max_execution_time:

============================================================
What is the maximum execution time for a Qiskit Runtime job?
============================================================

To ensure fairness, there is a maximum execution time for each Qiskit Runtime job. If
a job exceeds this time limit, it is forcibly cancelled. This is represented in the job
status as `Cancelled - Ran too long`. The maximum execution time is the
smaller of 1) the system limit and 2) the ``max_execution_time`` defined by the program.

The maximum execution time for the Sampler primitive is 10000 seconds (2.78 hours). The maximum execution time for the Estimator primitive is 18000 seconds (5 hours).

The system limit is defined as follows:

Qiskit Runtime on IBM Cloud
---------------------------

The system limit on the job execution time is 3 hours for a job running on a simulator
and 8 hours for a job running on a physical system.

Qiskit Runtime on IBM Quantum
-----------------------------

The system limit on the job execution time is described in the following table:

+------------------+--------------+-----------+--------------+-----------+
|                  | Public Program           | Private Program          |
+==================+==============+===========+==============+===========+
|                  | Premium User | Open User | Premium User | Open User |
+------------------+--------------+-----------+--------------+-----------+
| Simulated Device | 3h           | 1h        | 3h           | N/A       |
+------------------+--------------+-----------+--------------+-----------+
| Real Device      | 8h           | 4h        | 8h           | N/A       |
+------------------+--------------+-----------+--------------+-----------+

Note that a *premium user* here means a user who has access to backends in providers other than ibm-q/open/main.

Sessions
--------

When a session is started, it is assigned a maximum session timeout value.  After the maximum session timeout is reached, the session is permanently closed. The maximum session timeout value is set on the ``max_time`` parameter, which can be greater than the program’s ``max_execution_time``. By default, it is set to the initial job's maximum execution time and is the smaller of these values:
   *  The system limit
   *  The ``max_execution_time`` defined by the program

  Additionally, there is a 5 minute *interactive* timeout value. If there are no session jobs queued within that window, the session is temporarily deactivated and normal job selection resumes. After the new session becomes inactive, if the job scheduler gets a job from the original session and its maximum timeout value has not been reached, the session is reactivated until its maximum timeout value is reached.
  
  .. note:: The timer for ``max_time`` is not paused during any temporary deactivation periods. 

Other limitations
-----------------

- Programs cannot exceed 750KB in size.
- Inputs to jobs cannot exceed 64MB in size.