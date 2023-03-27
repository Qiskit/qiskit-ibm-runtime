Run a primitive in a session
=================================

A Qiskit Runtime session allows you to group a collection of iterative calls to the quantum computer. A session is started when the first job within the session is started. Provided that the session is active, subsequent jobs within the session are prioritized by the scheduler to minimize artificial delay within an iterative algorithm. Data used within a session, such as transpiled circuits, is also cached to avoid unnecessary overhead.
As a result, sessions allow you to more efficiently run programs that require iterative calls between classical and quantum resources while giving you the flexibility to deploy your programs remotely on cloud or on-premises classical resources (including your laptop).

Before you begin
----------------
Before starting a session, you must `Set up Qiskit Runtime <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/getting_started.html>`__ and initialize it as a service:

.. code-block:: python
  
  from qiskit_ibm_runtime import QiskitRuntimeService

  service = QiskitRuntimeService()

Run a job in a session
-------------------------------

You can set up a runtime session by using the context manager (``with ...:``), which automatically opens the session for you. A session is started when the first primitive job in this context manager starts. For example, the following code creates an Estimator instance inside a Session context manager.

Start by loading the options into a primitive constructor, then pass in circuits, parameters, and observables:

.. code-block:: python
  
  with Session(service) as session:
      estimator = Estimator(session=session, options=options) #primitive constructor
      estimator.run(circuit, parameters, observable) #job call
      job.result()
      # Close the session only if all jobs are finished, and you don't need to run more in the session
      session.close() 

Session options
-----------------

When you start your session, you can specify options, such as the backend to run on.  For the full list of options, see the `Sessions API documentation <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.Session.html#qiskit_ibm_runtime.Session>`__

**Example:**

.. code-block:: python

  with Session(service=service, backend="ibmq_qasm_simulator"):
      estimator = Estimator(options=options)
    
.. note::
  When running in IBM Cloud, if you don't specify a backend, the least busy backend is used. 

Full example
------------

This example starts a session, runs an Estimator job, and outputs the result:

.. code-block:: python

  from qiskit.circuit.random import random_circuit
  from qiskit.quantum_info import SparsePauliOp
  from qiskit_ibm_runtime import QiskitRuntimeService, Session, Estimator, Options

  circuit = random_circuit(2, 2, seed=1).decompose(reps=1)
  observable = SparsePauliOp("IY")

  options = Options()
  options.optimization_level = 2
  options.resilience_level = 2

  service = QiskitRuntimeService()
  with Session(service=service, backend="ibmq_qasm_simulator") as session:
      estimator = Estimator(session=session, options=options)
      job = estimator.run(circuit, observable)
      result = job.result()
      # Close the session only if all jobs are finished, and you don't need to run more in the session
      session.close()

  display(circuit.draw("mpl"))
  print(f" > Observable: {observable.paulis}")
  print(f" > Expectation value: {result.values[0]}")
  print(f" > Metadata: {result.metadata[0]}")


How long a session stays active
--------------------------------

When a session is started, it is assigned a maximum session timeout value.  You can set this value by using the ``max_time`` parameter, which can be greater than the program's ``max_execution_time``.


If you do not specify a timeout value, it is set to the initial job's maximum execution time and is the smaller of these values:

   * The system limit (8 hours for physical systems).
   * The ``max_execution_time`` defined by the program.

After this time limit is reached, the session is permanently closed and any queued jobs are put into an error state.

Additionally, there is an *interactive* timeout value. If there are no session jobs queued within that window, the session is temporarily deactivated and normal job selection resumes. After a session is deactivated, a subsequent job could start an additional session.  Jobs for the new session would then take priority until the new session deactivates or is closed. After the new session becomes inactive, if the job scheduler gets a job from the original session and its maximum timeout value has not been reached, the session is reactivated until its maximum timeout value is reached.

When you are done submitting jobs, you are encouraged to use ``session.close()`` to close the session. This allows the scheduler to run the next job without waiting for the session timeout. Remember, however, that you cannot submit more jobs to a closed session.

How session jobs fit into the job queue
------------------------------------------

For each backend, the first job in the session waits its turn in the queue normally, but while the session is active, subsequent jobs within the same session take priority over any other queued jobs. If there are no jobs that are part of a session, the next job from the regular fair-share queue is run. Jobs still run one at a time. Therefore, jobs that belong to a session still queue up if you already have one running, but you do not have to wait for them to complete before submitting more jobs.

.. note::
  Do not start a session inside of a reservation. If you use a session inside a reservation and not all of the session jobs finish during the reservation window, the pending jobs outside of the window might fail.   
