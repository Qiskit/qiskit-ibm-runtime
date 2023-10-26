Introduction to sessions 
=============================

A session allows a collection of jobs to be grouped and jointly scheduled by the Qiskit Runtime service, facilitating iterative use of quantum computers without incurring queuing delays on each iteration. This eliminates artificial delays caused by other users’ jobs running on the same quantum device during the session.

.. image:: images/session-overview.png 
  :width: 400

Compared with jobs that use the `fair-share scheduler <https://quantum-computing.ibm.com/lab/docs/iql/manage/systems/queue>`__, sessions become particularly beneficial when running programs that require iterative calls between classical and quantum resources, where a large number of jobs are submitted sequentially. This is the case, for example, when training a variational algorithm such as VQE or QAOA, or in device characterization experiments.

Runtime sessions can be used in conjunction with Qiskit Runtime primitives. Primitive program interfaces vary based on the type of task that you want to run on the quantum computer and the corresponding data that you want returned as a result. After identifying the appropriate primitive for your program, you can use Qiskit to prepare inputs, such as circuits, observables (for Estimator), and customizable options to optimize your job. For more information, see the `Primitives <primitives.html>`__ topic.

Benefits of using sessions
---------------------------

There are several benefits to using sessions:

* Jobs that belong to a single algorithm run are run together without interruption, increasing efficiency if your program submits multiple sequential jobs. 

   .. note:: 
    * The queuing time does not decrease for the first job submitted within a session. Therefore, a session does not provide any benefits if you only need to run a single job.
    * If the first session job is cancelled, subsequent session jobs will all fail. 

* When using sessions, the uncertainty around queuing time is significantly reduced. This allows better estimation of a workload's total runtime and better resource management.
* In a device characterization context, being able to run experiments closely together helps prevent device drifts and provide more accurate results.
* While the session is active, you can submit different jobs, inspect job results, and re-submit new jobs without opening a new session. 
* You maintain the flexibility to deploy your programs either remotely (cloud / on-premises) or locally (your laptop).

The mechanics of sessions (queuing)
----------------------------------------

For each backend, the first job in the session waits its turn in the queue normally, but while the session is active, subsequent jobs within the same session take priority over any other queued jobs. If no jobs that are part of the active session are ready, the session is deactivated (paused), and the next job from the regular fair-share queue is run. See :ref:`ttl` for more information.

A quantum processor still executes one job at a time. Therefore, jobs that belong to a session still need to wait for their turn if one is already running.  

.. note:: 
    * Internal systems jobs such as calibration have priority over session jobs.

Maximum session timeout
++++++++++++++++++++++++++++

When a session is started, it is assigned a *maximum session timeout*
value. You can set this value by using the ``max_time`` parameter, which
can be greater than the program's ``max_execution_time``. For
instructions, see `Run a primitive in a session <how_to/run_session.html>`__.

If you do not specify a timeout value, it is set to the system limit.

To find the maximum session timeout value for a session, follow the instructions in `Determine session details <how_to/run_session#determine-session-details.html>`__.


.. _ttl:

Interactive timeout value
+++++++++++++++++++++++++++++

Every session has an *interactive timeout value* (ITTL, or interactive time to live). If there are no session jobs queued within the
ITTL window, the session is temporarily deactivated and normal job
selection resumes. A deactivated session can be resumed if it has not
reached its maximum timeout value. The session is resumed when a
subsequent session job starts. Once a session is deactivated, its next
job waits in the queue like other jobs.

After a session is deactivated, the next job in the queue is selected to
run. This newly selected job (which can belong to a different user) can
run as a singleton, but it can also start a different session. In other
words, a deactivated session does not block the creation of other
sessions. Jobs from this new session would then take priority until it
is deactivated or closed, at which point normal job selection resumes.

To find the interactive timeout value for a session, follow the instructions in `Determine session details <how_to/run_session#determine-session-details.html>`__.   

.. _ends:

What happens when a session ends
-------------------------------------

A session ends by reaching its maximum timeout value,  when it is `closed <how_to/run_session#close_session.html>`__, or when it is canceled by using the `session.cancel()` method. What happens to unfinished session jobs when the session ends depends on how it ended:


.. note::  
        Previously, `session.close()` **canceled** the session.  Starting with `qiskit-ibm-runtime` 0.13, `session.close()` **closes** the session. The `session.cancel()` method was added in `qiskit-ibm-runtime` 0.13.
  
If the maximum timeout value was reached:
    -   Any jobs that are already running continue to run.
    -   Any queued jobs remaining in the session are put into a failed state.
    -   No further jobs can be submitted to the session.
    -   The session cannot be reopened.

If the maximum timeout value has not been reached:    

- When using `qiskit-ibm-runtime` 0.13 or later releases:
    - If a session is closed:
        - Session status becomes "In progress, not accepting new jobs".
        - New job submissions to the session are rejected.
        - Queued or running jobs continue to run.
        - The session cannot be reopened.
    - If a session is canceled:
        - Session status becomes "Closed."
        - Running jobs continue to run.
        - Queued jobs are put into a failed state.
        - The session cannot be reopened.

- When using Qiskit Runtime releases before 0.13:
    -   Any jobs that are already running continue to run.
    -   Any queued jobs remaining in the session are put into a failed state.
    -   No further jobs can be submitted to the session.
    -   The session cannot be reopened.

Different ways of using sessions
----------------------------------

Sessions can be used for iterative or batch execution. 

Iterative
+++++++++++++++++++++

Any session job submitted within the five-minute interactive timeout, also known as interactive time to live (ITTL), is processed immediately. This allows some time for variational algorithms, such as VQE, to perform classical post-processing. 

- When a session is active, its jobs get priority until ITTL or max timeout is reached.
- Post-processing could be done anywhere, such as a personal computer, cloud service, or an HPC environment.

.. image:: images/iterative.png 

.. note::
    There might be a limit imposed on the ITTL value depending on whether your hub is Premium, Open, and so on. 

This is an example of running an iterative workload that uses the classical SciPy optimizer to minimize a cost function. In this model, SciPy uses the output of the cost function to calculate its next input. 

.. code-block:: python
    
    def cost_func(params, ansatz, hamiltonian, estimator):
        # Return estimate of energy from estimator

        energy = estimator.run(ansatz, hamiltonian, parameter_values=params).result().values[0]
        return energy

    x0 = 2 * np.pi * np.random.random(num_params)

    session = Session(backend=backend)

    estimator = Estimator(session=session, options={"shots": int(1e4)})
    res = minimize(cost_func, x0, args=(ansatz, hamiltonian, estimator), method="cobyla")

    # Close the session because we didn't use a context manager.
    session.close()
  

Batch
+++++++++++++++++++++

Ideal for running experiments closely together to avoid device drifts, that is, to maintain device characterization.

- Suitable for batching many jobs together. 
- The parts of the jobs that are processed classically run in parallel, and the quantum pieces run sequentially on hardware, which saves you time.


.. note::  
    When batching, jobs are not guaranteed to run in the order they are submitted.    

.. image:: images/batch.png 

The following example shows how you can divide up a long list of circuits into multiple jobs and run them as a batch to take advantage of the parallel processing.

.. code-block:: python

    backend = service.backend("ibm_sherbrooke")

    with Session(backend=backend):
        estimator = Estimator()
        start_idx = 0
        jobs = []
        while start_idx < len(circuits):
            end_idx = start_idx + backend.max_circuits
            jobs.append(estimator.run(circuits[start_idx:end_idx], obs[start_idx:end_idx], params[start_idx:end_idx]))
            start_idx = end_idx

Sessions and reservations 
-------------------------

IBM Quantum Premium users can access both reservations and sessions on specific backends. Such users should plan ahead and decide whether to use a session or a reservation. You *can* use a session within a reservation.  However, if you use a session within a reservation and some session jobs don’t finish during the reservation window, the remaining pending jobs might fail. If you use session inside a reservation, we suggest you set a realistic ``max_time`` value.

.. image:: images/jobs-failing.png 

Summary
---------

- Jobs within an active session take priority over other queued jobs.
- A session becomes active when its first job starts running.
- A session stays active until one of the following happens:
  - Its maximum timeout value is reached. In this case all queued jobs are canceled, but running jobs will finish. 
  - Its interactive timeout value is reached. In this case the session is deactivated but can be resumed if another session job starts running. 
  - The session is closed or cancelled. This can be done using the corresponding methods or upon exiting a session context.
- Sessions can be used for iterative or batch execution.

Next steps
------------

`Run a primitive in a session <how_to/run_session.html>`__
