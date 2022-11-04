Working with sessions
===========================

A Qiskit Runtime session allows you to group a collection of iterative calls to the quantum computer. A session is started when the first job within the session is started. As long as the session is active, subsequent jobs within the session are prioritized by the scheduler to minimize artificial delay within an iterative algorithm. Data used within a session, such as transpiled circuits, is also cached to avoid unnecessary overhead.
As a result, sessions allow you to more efficiently run programs that require iterative calls between classical and quantum resources while giving you the flexibility to deploy your programs remotely on cloud or on-premise classical resources (including your laptop).

How to run a job in a session
-------------------------------

You can set up a Runtime session by using the context manager (`with ...:`), which automatically opens and closes the session for you. A session is started when the first primitive job in this context manager starts. For example, the following code creates an Estimator instance inside a Session context manager.

Start by loading the options into a primitive constructor, then pass in circuits, parameters, and observables:

.. code-block:: python
  
  with Session(service) as session:
    estimator = Estimator(session=session, options=options) #primitive constructor
    estimator.run(circuit, parameters, observable) #job call


How session jobs fit into the job queue
------------------------------------------

For each backend, the first job in the session waits its turn in the queue normally, but while the session is active, subsequent jobs within the same session take priority over any other queued jobs. If there are no jobs that are part of a session, the next job from the regular fair-share queue is run. Jobs still run one at a time. Thus, jobs that belong to a session still queue up if you already have one running, but you do not have to wait for them to complete before submitting more jobs.

How long a session stays active
--------------------------------

When a session is started, it is assigned a maximum session timeout value.  You can set this value by using the `max_time` parameter, which can be greater than the program’s `max_execution_time`.


If you do not specify a timeout value, it is set to the initial job's maximum execution time and is the smaller of these values:

   * The system limit (8 hours for physical systems).
   * The `max_execution_time` defined by the program.

After this time limit is reached, the session is permanently closed.

Additionally, there is an *interactive* timeout value. If there are no session jobs queued within that window, the session is temporarily deactivated and normal job selection resumes. After a session is deactivated, a subsequent job could start an additional session.  Jobs for the new session would then take priority until the new session deactivates or is closed. After the new session becomes inactive, if the job scheduler gets a job from the original session and its maximum timeout value has not been reached, the session is reactivated until its maximum timeout value is reached.

When using primitives with their context managers as previously described, the session is closed automatically when the block is exited.
