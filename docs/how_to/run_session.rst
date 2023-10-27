Run jobs in a session
=================================

There are several ways to set up and use sessions. The following information should not be considered mandatory steps to follow. Instead, choose the configuration that best suits your needs. To learn more about sessions, see `Introduction to sessions <../sessions.html>`__. This information assumes that you are using Qiskit Runtime `primitives <../primitives.html>`__.

Prerequisites
--------------

Before starting a session, you must `Set up Qiskit Runtime <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/getting_started.html>`__ and initialize it as a service:

.. code-block:: python

  from qiskit_ibm_runtime import QiskitRuntimeService

  service = QiskitRuntimeService()

Open a session
-----------------

You can open a runtime session by using the context manager `with Session(…)` or by initializing the `Session` class. When you start a session, you can specify options, such as the backend to run on. This topic describes the most commonly used options.  For the full list, see the `Sessions API documentation <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.Session.html#qiskit_ibm_runtime.Session>`__.

.. important::
  Data from the first session job is cached and used by subsequent jobs.  Therefore, if the first job is cancelled, subsequent session jobs will all fail.

**Session class**

A session can be created by initializing the `Session` class, which can then be passed to the desired primitives. Example:

.. code-block:: python

  session= Session(service=service, backend="ibmq_qasm_simulator")
  estimator = Estimator(session=session)
  sampler = Sampler(session=session)

**Context manager**

The context manager automatically opens and closes a session for you. A session is started when the first primitive job in this context manager starts (not when it is queued).  Primitives created in the context automatically use that session. Example:

.. code-block:: python

  with Session(service=service, backend="ibmq_qasm_simulator"):
    estimator = Estimator()
    sampler = Sampler()


Specify a backend
-----------------

When you start a session, you can specify session options, such as the backend to run on. A backend is required if you are using the IBM Quantum channel, but optional if you are using the IBM Cloud channel. Once specified, you cannot change the backend used for a session and you cannot specify multiple backends within a session.  To use a different backend, open a new session.

There are two ways to specify a backend in a session:

**Directly specify a string with the backend name.** Example:

  .. code-block:: python

    backend = "ibmq_qasm_simulator"
    with Session(backend=backend):
      ...

**Pass the backend object.** Example:

  .. code-block:: python

    backend = service.get_backend("ibmq_qasm_simulator")
    with Session(backend=backend):
      ...

.. _session_length:

Specify the session length
--------------------------

When a session is started, it is assigned a maximum session timeout value. After the session has been open the specified amount of time, the session expires and is forcefully closed. You can no longer submit jobs to that session.  See `What happens when a session ends <../sessions.html#ends>`__ for further details.

You can configure the maximum session timeout value through the ``max_time`` parameter, which can be specified as seconds (int) or a string, like "2h 30m 40s".  This value has to be greater than the ``max_execution_time`` of the job and less than the system’s ``max_time``. The default value is the system’s ``max_time``. See `Determine session details <#determine-session-details>`__ to determine the system limit.

When setting the session length, consider how long each job within the session might take. For example, if you run five jobs within a session and each job is estimated to be five minutes long, the maximum time for the session should at least 25 min.

.. code-block:: python

  with Session(service=service, backend=backend, max_time="25m"):
    ...

There is also an interactive timeout value (ITTL) that cannot be configured.  If no session jobs are queued within that window, the session is temporarily deactivated. For more details about session length and timeout, see `How long a session stays active <../sessions.html#active>`__. To determine a session's ITTL, follow the instructions in `Determine session details <#determine-session-details>`__ and look for the ``interactive_timeout`` value.


.. _close_session:

Close a session
---------------

With `qiskit-ibm-runtime` 0.13 or later releases, when the session context manager is exited, the session is put into `In progress, not accepting new jobs` status.  This means that the session will finish processing all running or queued jobs until the maximum timeout value is reached.  After all jobs are completed, the session is immediately closed. This allows the
scheduler to run the next job without waiting for the session interactive timeout,
therefore reducing the average job queueing time. You cannot submit jobs to a
closed session.

This behavior exists in `qiskit-ibm-runtime` 0.13 or later releases only. Previously, `session.close()` **canceled** the session. 

.. code-block:: python

  with Session(service=service, backend=backend):
      estimator = Estimator()
      job = estimator.run(...)
      
  # The session is no longer accepting jobs but the submitted job will run to completion    
  result = job.result()

.. _cancel_session:

Cancel a session
----------------

If a session is canceled, the session is put into `Closed` status.  Any jobs that are already running continue to run but queued jobs are put into a failed state and no further jobs can be submitted to the session. This is a convenient way to quickly fail all queued jobs within a session. 

### For Qiskit runtime releases 0.13 or later

Use the `session.cancel()` method to cancel a session.  

.. code-block:: python

  with Session(service=service, backend=backend) as session:
      estimator = Estimator()
      job1 = estimator.run(...)
      job2 = estimator.run(...)
      # You can use session.cancel() to fail all pending jobs, for example, 
      # if you realize you made a mistake.
      session.cancel()

For Qiskit Runtime releases 0.13 or later
+++++++++++++++++++++++++++++++++++++++++

Use the `session.cancel()` method to cancel a session.  

.. code-block:: python

  with Session(service=service, backend=backend) as session:
      estimator = Estimator()
      job1 = estimator.run(...)
      job2 = estimator.run(...)
      # You can use session.cancel() to fail all pending jobs, for example, 
      # if you realize you made a mistake.
      session.cancel()

For Qiskit Runtime releases before 0.13
+++++++++++++++++++++++++++++++++++++++++

Use the `session.close()` method to cancel a session.  This allows the
scheduler to run the next job without waiting for the session timeout,
therefore making it easier for everyone. You cannot submit jobs to a
closed session.

.. code-block:: python

  with Session(service=service, backend=backend) as session:
    estimator = Estimator()
    job = estimator.run(...)
    # Do not close here, the job might not be completed!
    result = job.result()
    # Reaching this line means that the job is finished.
    # This close() method would fail all pending jobs.
    session.close()
  
Invoke multiple primitives in a session
----------------------------------------
You are not restricted to a single primitive function within a session. In this section we will show you an example of using multiple primitives. 

First we prepare a circuit for the Sampler primitive.

.. code-block:: python

  from qiskit.circuit.random import random_circuit

  sampler_circuit = random_circuit(2, 2, seed=0).decompose(reps=1)
  sampler_circuit.measure_all()
  display(circuit.draw("mpl"))

The following example shows how you can create both an instance of the `Sampler` class and one of the `Estimator` class and invoke their `run()` methods within a session. 

.. code-block:: python

  from qiskit_ibm_runtime import Session, Sampler, Estimator

  with Session(backend=backend):
    sampler = Sampler()
    estimator = Estimator()

    result = sampler.run(sampler_circuit).result()
    print(f">>> Quasi-probability distribution from the sampler job: {result.quasi_dists[0]}")

    result = estimator.run(circuit, observable).result()
    print(f">>> Expectation value from the estimator job: {result.values[0]}")

The calls can also be synchronous. You don’t need to wait for the result of a previous job before submitting another one, as shown below:

.. code-block:: python

  from qiskit_ibm_runtime import Session, Sampler, Estimator

  with Session(backend=backend):
    sampler = Sampler()
    estimator = Estimator()

    sampler_job = sampler.run(sampler_circuit)
    estimator_job = estimator.run(circuit, observable)

    print(
        f">>> Quasi-probability distribution from the sampler job: {sampler_job.result().quasi_dists[0]}"
    )
    print(f">>> Expectation value from the estimator job: {estimator_job.result().values[0]}")

.. _session_status:

Query session status
---------------------    


You can query the status of a session using `session.status()`.  You can also view a session's status on the Jobs page for your channel.

Session status can be one of the following:

- `Pending`: Session has not started or has been deactivated. The next session job needs to wait in the queue like other jobs. 
- `In progress, accepting new jobs`: Session is active and accepting new jobs.
- `In progress, not accepting new jobs`: Session is active but not accepting new jobs. Job submission to the session will be rejected, but outstanding session jobs will run to completion. The session will be automatically closed once all jobs finish. 
- `Closed`: Session maximum timeout value has been reached, or session was explicitly closed.

.. _session_details:

Determine session details
--------------------------  

You can find details about a session by using the `session.details()` method, from the `Quantum Platform Jobs page <https://quantum-computing.ibm.com/jobs>`__, or from the IBM Cloud Jobs page, which you access from your `Instances page <https://cloud.ibm.com/quantum/instances>`__. From the session details you can determine the `maximum <..sessions#max-ttl.html>`__ and `interactive <..sessions#ttl.html>`__ time to live (TTL) values, its status, whether it's currently accepting jobs, and more. 

Example:

.. code-block:: python

  from qiskit_ibm_runtime import QiskitRuntimeService

  service = QiskitRuntimeService()

  with Session(service=service, backend="ibmq_qasm_simulator") as session:
      estimator = Estimator()
      job = estimator.run(circuit, observable)
      print(session.details())

Output:

.. code-block:: text

  {
  'id': 'cki5d18m3kt305s4pndg',
    'backend_name': 'ibm_algiers',
    'interactive_timeout': 300,  # This is the interactive timeout, in seconds
    'max_time': 28800,           # This is the maximum session timeout, in seconds
    'active_timeout': 28800,
    'state': 'closed',
    'accepting_jobs': True,
    'last_job_started': '2023-10-09T19:37:42.004Z',
    'last_job_completed': '2023-10-09T19:38:10.064Z',
    'started_at': '2023-10-09T19:37:42.004Z',
    'closed_at': '2023-10-09T19:38:39.406Z'
  }


Full example
------------

In this example, we start a session, run an Estimator job, and output the result:

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
  with Session(service=service, backend="ibmq_qasm_simulator"):
      estimator = Estimator(options=options)
      job = estimator.run(circuit, observable)
      result = job.result()

  display(circuit.draw("mpl"))
  print(f" > Observable: {observable.paulis}")
  print(f" > Expectation value: {result.values[0]}")
  print(f" > Metadata: {result.metadata[0]}")