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
   As of August 7, 2023, the ``max_execution_time`` value is based on system execution time, which is the time that the QPU
   complex (including control software, control electronics, QPU, and so on) is engaged in
   processing the job, instead of wall clock time.

   Simulator jobs continue to use wall clock time.

You can set the maximum execution time (in seconds) on the job options by using one of the following methods:

.. code-block:: python

   # Initiate the Options class with parameters
   options = Options(max_execution_time=360)

.. code-block:: python

   # Create the options object with attributes and values
   options = {"max_execution_time": 360}

You can also find the system execution time for previously completed jobs by using:

.. code-block:: python

   # Find the system execution time
   print(f"Job {job.job_id()} system execution time was {job.metrics()['usage']['seconds']} seconds")

In addition, the system calculates an appropriate job timeout value based on the
input circuits and options. This system-calculated timeout is currently capped
at 3 hours to ensure fair device usage. If a ``max_execution_time`` is
also specified for the job, the lesser of the two values is used.

For example, if you specify ``max_execution_time=5000``, but the system determines
it should not take more than 5 minutes (300 seconds) to execute the job, then the job will be
cancelled after 5 minutes.

Session maximum execution time
*******************************

When a session is started, it is assigned a maximum session timeout value. After this timeout is reached, the session is terminated, any jobs that are already running continue running, and any queued jobs that remain in the session are put into a failed state.  For instructions to set the session maximum time, see `Specify the session length <../how_to/run_session#session_length.html>`__.


Other limitations
***************************

- Programs cannot exceed 750KB in size.
- Inputs to jobs cannot exceed 64MB in size.
- Open plan users can use up to 10 minutes of system execution time per month (resets at 00:00 UTC on the first of each month). System execution time is the amount of time that the system is dedicated to processing your job. You can track your monthly usage on the `Platform dashboard, <https://quantum-computing.ibm.com/>`__ `Jobs, <https://quantum-computing.ibm.com/jobs>`__ and `Account <https://quantum-computing.ibm.com/account>`__ page.