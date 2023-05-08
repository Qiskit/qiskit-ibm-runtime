.. _faqs/max_execution_time:

============================================================
What is the maximum execution time for a Qiskit Runtime job?
============================================================

To ensure fairness, there is a maximum execution time for each Qiskit Runtime job. If
a job exceeds this time limit, it is forcibly cancelled. This is represented in the job
status as `Cancelled - Ran too long`. The maximum execution time is the
smaller of these values: 

- The system limit 
- The ``max_execution_time`` defined by the program
- The ``max_execution_time`` defined by the job itself

The system limit depends on the channel you're using and is defined as follows:

IBM Cloud system limit
***************************

The system limit on the Qiskit Runtime job execution time is 3 hours for a job running on a simulator
and 8 hours for a job running on a physical system.

 IBM Quantum system limit
*****************************

The system limit on the Qiskit Runtime job execution time is described in the following table:

+------------------+--------------+------------------+--------------+-----------+
|                  | Primitives & prototype programs | Private programs         |
+==================+==============+==================+==============+===========+
|                  | Premium User | Open User        | Premium User | Open User |
+------------------+--------------+------------------+--------------+-----------+
| Simulated Device | 3h           | 1h               | 3h           | N/A       |
+------------------+--------------+------------------+--------------+-----------+
| Real Device      | 8h           | 4h               | 8h           | N/A       |
+------------------+--------------+------------------+--------------+-----------+

Note that a *premium user* here means a user who has access to backends in providers other than ibm-q/open/main.

Program time limits
***************************

In addition to the ``max_execution_time`` parameter, different types of programs have their own time limits:

* **Primitives:** The maximum execution time for the Sampler primitive is 10000 seconds (2.78 hours). The maximum execution time for the Estimator primitive is 18000 seconds (5 hours).
* **Prototype programs:** The maximum execution time is listed on the `Prototype programs page <https://quantum-computing.ibm.com/services/programs/prototypes>`__. 
* **Private Programs:** The maximum execution time (in seconds) for a program is set on the job options with the ``max_execution_time`` parameter. 

Job max execution time
***************************

Set the maximum execution time (in seconds) on the job options by using one of the following methods.  The value must be **300 or higher**:

.. code-block:: python

   # Initiate the Options class with parameters 
   options = Options(max_execution_time=360)

.. code-block:: python

   # Create the options object with attributes and values 
   options = {"max_execution_time": 360}

Session time limits
***************************

When a session is started, it is assigned a maximum session timeout value (by default, it is set to the system limit).  After the maximum session timeout is reached, the session is permanently closed. The maximum session timeout value is set on the ``max_time`` parameter, which can be greater than the program’s ``max_execution_time``. 

Additionally, there is a 5 minute *interactive* timeout value. If there are no session jobs queued within that window, the session is temporarily deactivated and normal job selection resumes. During job selection, if the job scheduler gets a new job from the session and its maximum timeout value has not been reached, the session is reactivated until its maximum timeout value is reached.
  
.. note:: The timer for the session's ``max_time`` is not paused during any temporary deactivation periods. 


Other limitations
***************************

- Programs cannot exceed 750KB in size.
- Inputs to jobs cannot exceed 64MB in size.