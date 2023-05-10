Introduction to sessions 
=============================

A session is a contract between the user and the Qiskit Runtime service that ensures that a collection of jobs can be grouped and jointly prioritized by the quantum computer’s job scheduler. This eliminates artificial delays caused by other users’ jobs running in your same quantum device during the session time.

.. image:: images/session-overview.png 

In simple terms, once your session is active, jobs submitted within the session will not be interrupted by other users’ jobs.     

Compared with fair-share, sessions become particularly beneficial when running programs that require iterative calls between classical and quantum resources, where a large number of jobs is submitted sequentially. This is the case, for example, when training a variational algorithm such as VQE or QAOA, or in device characterization experiments.

Note : see details on the Faire-share scheduler - https://quantum-computing.ibm.com/lab/docs/iql/manage/systems/queue

Benefits of using sessions
---------------------------

* Jobs belonging to a single algorithm run will be run together without interruptions, increasing efficiency if your program submits multiple sequential jobs. 
   Note: the queuing time does not decrease for a single job submitted within a session.
* When using sessions, the uncertainty around queuing time is significantly reduced. This allows for a better estimation of a workload’s total runtime, and better resource management.
* In a device characterization context, being able to run experiments closely together helps prevent device drifts and provide more accurate results.
* As long as the session is active, you can submit different jobs, inspect job results and re-submit new jobs without having to open a new session every time. 
  Note:  Sessions have an interactive timeout value. If no jobs are sent within this time, the session is deactivated until a new job is sent, and the device will allow other user’s jobs to run in the meantime, see TTL section for further information.
* You maintain the flexibility to deploy your programs either remotely (cloud/on-premise) or locally (your laptop).

The mechanics of sessions (queuing)
----------------------------------------

Primitive program interfaces vary based on the type of task that you want to run on the quantum computer and the corresponding data that you want returned as a result. After identifying the appropriate primitive for your program, you can use Qiskit to prepare inputs, such as circuits, observables (for Estimator), and customizable options to optimize your job. For more information, see the appropriate topic:

