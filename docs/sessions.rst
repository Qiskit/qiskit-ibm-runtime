Introduction to sessions 
=============================

A session is a contract between the user and the Qiskit Runtime service that ensures that a collection of jobs can be grouped and jointly prioritized by the quantum computer’s job scheduler. This eliminates artificial delays caused by other users’ jobs running on the same quantum device during the session time.

.. image:: images/session-overview.png 
  :width: 400

In simple terms, once your session is active, jobs submitted within the session will not be interrupted by other users’ jobs.     

Compared with jobs that use the `fair-share scheduler <https://quantum-computing.ibm.com/lab/docs/iql/manage/systems/queue>`__, sessions become particularly beneficial when running programs that require iterative calls between classical and quantum resources, where a large number of jobs are submitted sequentially. This is the case, for example, when training a variational algorithm such as VQE or QAOA, or in device characterization experiments.

Runtime sessions only work with Qiskit Runtime primitives. Primitive program interfaces vary based on the type of task that you want to run on the quantum computer and the corresponding data that you want returned as a result. After identifying the appropriate primitive for your program, you can use Qiskit to prepare inputs, such as circuits, observables (for Estimator), and customizable options to optimize your job. For more information, see the `Primitives <primitives.html>`__ topic.

Benefits of using sessions
---------------------------

There are several benefits to using sessions:

* Jobs that belong to a single algorithm run are run together without interruptions, increasing efficiency if your program submits multiple sequential jobs. 

   .. note:: 
    * The queuing time does not decrease for a single job submitted within a session.
    * Since data from the first session job is cached and used by subsequent jobs, if the first job is cancelled, subsequent session jobs will all fail. 

* When using sessions, the uncertainty around queuing time is significantly reduced. This allows better estimation of a workload's total runtime and better resource management.
* In a device characterization context, being able to run experiments closely together helps prevent device drifts and provide more accurate results.
* As long as the session is active, you can submit different jobs, inspect job results, and re-submit new jobs without having to open a new session every time. 
* You maintain the flexibility to deploy your programs either remotely (cloud / on-premise) or locally (your laptop).

The mechanics of sessions (queuing)
----------------------------------------

For each backend, the first job in the session waits its turn in the queue normally, but while the session is active, subsequent jobs within the same session take priority over any other queued jobs. If there are no jobs that are part of the active session ready, the session is deactivated (paused), and the next job from the regular fair-share queue is run. See :ref:`ttl` for more information.

Session jobs still run one at a time. Therefore, jobs that belong to a session still queue up while one is running, but you do not have to wait for it to complete before submitting more jobs and they do not go through the fair-share queue.  

.. note:: 
    Systems jobs such as calibration have priority over session jobs.

Iterations vs Batching 
--------------------------

Sessions can be used in iterations or by batching. 

Iterative sessions
+++++++++++++++++++++

Any session job submitted within the five minute interactive timeout (TTL) is processed immediately. This allows some time for variational algorithms, such as VQE, to perform classical post processing. 

- The quantum device is locked to the session user unless the TTL is reached. 
- Post-processing could be done anywhere, such as a personal computer, cloud service, or an HPC environment.

.. image:: images/iterative.png 

Batch sessions
+++++++++++++++++++++

Ideal for running experiments closely together to avoid device drifts, that is, to maintain device characterzation.

- Suitable for batching many jobs together. 
- Jobs that fit within the maximum session time run back-to-back on hardware.

.. note::  
    When batching, jobs are not guaranteed to run in the order they are submitted.    

.. image:: images/batch.png 

Sessions and reservations 
-------------------------

If you are an IBM Quantum Premium user, you get access to both reservations and sessions on specific backends. You should plan ahead and decide whether to use a session or a reservation. You can use a session within a reservation.  However, if you use a session within a reservation and some session jobs don’t finish during the reservation window, the remaining pending jobs might fail. If you use session inside a reservation we recommend that you set a realistic `max_execution` time.

.. image:: images/jobs-failing.png 

How long a session stays active
--------------------------------

The length of time a session is active is controlled by the *maximum session timeout* (`max_time`) value and the *interactive* timeout value* (TTL). The `max_time` timer starts when the session becomes active.  That is, when the first job runs, not when it is queued. It does not stop if a session becomes inactive. The TTL timer starts each time a session job finishes. 

Maximum session timeout
++++++++++++++++++++++++++++

When a session is started, it is assigned a *maximum session timeout* value.  You can set this value by using the ``max_time`` parameter, which can be greater than the program's ``max_execution_time``. For details, see `Run a primitive in a session <how_to/run_session.html>`__.


If you do not specify a timeout value, it is set to the initial job's maximum execution time and is the smaller of these values:

   * The system limit (see `What is the maximum execution time for a Qiskit Runtime job? <faqs/max_execution_time.html>`__).
   * The ``max_execution_time`` defined by the program.

.. _ttl:

Interactive timeout value
+++++++++++++++++++++++++++++

Every session has an *interactive timeout value* (TTL) of 5 minutes, which cannot be changed. If there are no session jobs queued within the TTL window, the session is temporarily deactivated and normal job selection resumes. A deactivated session can be resumed if its maximum timeout value has not been reached. The session is resumed when a subsequent sesssion job starts. Once a session is deactivated, its next job waits in the queue like other jobs. 

After a session is deactivated, the next job in the queue is selected to run. This newly selected job (which can belong to a different user) can run as a singleton, but it can also start a different session. In other words, a deactivated session does not block the creation of other sessions. Jobs from this new session would then take priority until it is deactivated or closed, at which point normal job selection resumes. 

What happens when a session ends
-------------------------------------

A session ends by reaching its maximum timeout value or when it is manually closed by the user.  Do not close a session until all jobs **complete**. See `Close a session <how_to/run_session#close session.html>`__ for details. After a session is closed, the following occurs:

* Any queued jobs remaining in the session are put into a failed state.
* Any session jobs that are not yet queued are moved to the regular fair-share queue, and they might fail if the cache job's data is expired.
* No further jobs can be submitted to the session.
* The session cannot be reopened. 


Next steps
------------

`Run a primitive in a session <how_to/run_session.html>`__