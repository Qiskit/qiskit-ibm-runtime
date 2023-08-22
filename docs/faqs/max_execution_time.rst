.. _faqs/max_execution_time:

=======================================================================
What is the maximum execution time for a Qiskit Runtime job or session?
=======================================================================

Job maximum execution time
***************************

To ensure fairness, and as a way to help control cost, there is a
maximum execution time for each Qiskit Runtime job. If
a job exceeds this time limit, it is forcibly cancelled and a ``RuntimeJobMaxTimeoutError``
exception is raised.

.. note::
   As of ``qiskit-ibm-runtime`` 0.12.0, the ``max_execution_time`` value is based on quantum
   time instead of wall clock time. Quantum time represents the time that the QPU
   complex (including control software, control electronics, QPU, and so on) is engaged in
   processing the job.

   Simulator jobs continue to use wall clock time because they do not have quantum time.

You can set the maximum execution time (in seconds) on the job options by using one of the following methods:

.. code-block:: python

   # Initiate the Options class with parameters
   options = Options(max_execution_time=360)

.. code-block:: python

   # Create the options object with attributes and values
   options = {"max_execution_time": 360}

You can also find quantum time used by previously completed jobs by using:

.. code-block:: python

   # Find quantum time used by the job
   print(f"Quantum time used by job {job.job_id()} was {job.metrics()['usage']['quantum_seconds']} seconds")

In addition, the system calculates an appropriate job timeout value based on the
input circuits and options. This system-calculated timeout is currently capped
at 3 hours to ensure fair device usage. If a ``max_execution_time`` is
also specified for the job, the lesser of the two values is used.

For example, if you specify ``max_execution_time=5000``, but the system determines
it should not take more than 5 minutes (300 seconds) to execute the job, then the job will be
cancelled after 5 minutes.

Session time limits
***************************

When a session is started, it is assigned a maximum session timeout value.
After this timeout is reached, the session is terminated and any queued jobs that remain in the session are put into a ``failed`` state.
You can set the maximum session timeout value using the ``max_time`` parameter:

.. code-block:: python

   # Set the session max time
   with Session(max_time="1h"):
       ...

If you don't specify a session ``max_time``, the system defaults are used:

+--------------+------------------+--------------+-----------+
| Primitive programs              | Private programs         |
+==============+==================+==============+===========+
| Premium User | Open User        | Premium User | Open User |
+--------------+------------------+--------------+-----------+
| 8h           | 4h               | 8h           | N/A       |
+--------------+------------------+--------------+-----------+

Note that a *premium user* here means a user who has access to backends in providers other than ``ibm-q/open/main``.

.. note::
   Session ``max_time`` is based on wall clock time, not quantum time.


Additionally, there is a 5 minute *interactive* timeout value. If there are no session jobs queued within that window, the session is temporarily deactivated and normal job selection resumes. During job selection, if the job scheduler gets a new job from the session and its maximum timeout value has not been reached, the session is reactivated until its maximum timeout value is reached.

.. note:: The timer for the session's ``max_time`` is not paused during any temporary deactivation periods.


Other limitations
***************************

- Programs cannot exceed 750KB in size.
- Inputs to jobs cannot exceed 64MB in size.