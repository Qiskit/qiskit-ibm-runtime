Run a primitive in a session
=================================

There are several ways to set up and use sessions. The following information should not be considered mandatory steps to follow. Instead, choose the configuration that best suits your needs. To learn more about sessions, see `Introduction to sessions <../sessions.html>`__.

Prerequisites
--------------

Runtime sessions only work with Qiskit Runtime `primitives <../primitives.html>`__. Before starting a session, you must `Set up Qiskit Runtime <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/getting_started.html>`__ and initialize it as a service:

.. code-block:: python
  
  from qiskit_ibm_runtime import QiskitRuntimeService

  service = QiskitRuntimeService()

Open a session
-----------------

You can open a runtime session by using the context manager `with Session(…)` or by initializing the `Session` class.

**Session class**

A session can be created by initializing the Session class, which can then be passed to the desired primitives. Example:

.. code-block:: python
  
  session= Session(service=service, backend="ibmq_qasm_simulator")
  estimator = Estimator(session=session)
  sampler = Sampler(session=session)

**Context manager**

The context manager automatically opens a session for you. A session is started when the first primitive job in this context manager starts (not when it is queued).  Primitives created in the context automatically use that session. Example:

.. code-block:: python
  
  with Session(service=service, backend="ibmq_qasm_simulator"):
    estimator = Estimator()
    sampler = Sampler()


Specify a backend
-----------------

When you start a session, you can specify session options, such as the backend to run on. A backend is required if you are using the IBM Quantum premium channel, but optional if you are using the IBM Pay-go Cloud channel. Once specified, you cannot change the backend used for a session, you would have to open a new one. There are two ways to specify a backend in a session.

.. note::
  You cannot have multiple backends within a session.

**Directly specify a string with the backend name.** Example: 
 
  .. code-block:: python

    backend = "ibmq_qasm_simulator"
    with Session(service=service, backend=backend):
      ...

**Pass the backend object.** Example: 

  .. code-block:: python

    backend = service.get_backend("ibmq_qasm_simulator")
    with Session(service=service, backend=backend):
      ...


Specify the session length
--------------------------

When a session is started, it is assigned a maximum session timeout value. Once the session has been open the specified amount of time, the session expires and is forcefully closed. You can no longer submit jobs to that session.

You can configure the maximum session timeout value through the `max_time` parameter, which can be specified as seconds (int) or a string, like "2h 30m 40s".  This value has to be greater then the `max_execution_time` of the job  and less than the system’s `max_time`. The default value is the system’s `max_time` (see table below).  For example, if you run five jobs within a session and each job is estimated to be five minutes long, the maximum time for you session should at least 25 min. 

.. code-block:: python

  with Session(service=service, backend=backend, max_time="25m"):
    ...   

There is also an interactive timeout value (5 minutes), which is not configurable.  If no session jobs are queued within that window, the session is temporarily deactivated. For more details about session length and timeout, see `sessions <../sessions.html>`__. 

.. _close session:
  
Close a session
---------------

When jobs are all done, we recommend to use session.close() to close the session. This allows the scheduler to run the next job without waiting for the session timeout. (therefore making it easy for everyone).  You cannot submit more jobs to a closed session.  

       .. warning::  A session should only be closed when all session jobs FINISHES, not just when one is done submitting. Otherwise jobs will be converted to fairshare and likely time out. 

       Note: Since data from the first session job is cached and used by subsequent jobs, if the first job is cancelled, subsequent session jobs will all fail. 

.. code-block:: python

  with Session(service=service, backend=backend) as session:
  ... 
  estimator = Estimator()
  job = estimator.run(...)
  # do not close here, the job might not be completed
  result = job.result()
  # reaching this line will mean that the job is finished
  session.close()

Retrieve job results
--------------------

You can review job results  immediately after the job completes by calling the the appropriate command:

*  `job.result()` - Review job results immediately after the job completes. 
* job.job_id() - Get the ID of the job 
* job.status() - Check the status of the job
* job = service.job(job_id) - Calling `job.job_id()` returns the job ID, which uniquely identifies that particular job. You can call `service.job(<job ID>)` to retrieve a job you previously submitted. Since the job ID is required in this call, it is recommended that you save the IDs of jobs you may want to retrieve later. If you don't have the job ID, or if you want to retrieve multiple jobs at once, you can call `service.jobs()` with optional filters instead. 

  Jobs are also listed on the Jobs page for your quantum service channel:


  * If you are using the IBM Cloud channel, from the IBM Cloud console quantum `Instances page <https://cloud.ibm.com/quantum/instances>`__, click the name of your instance, then click the Jobs tab. To see the status of your job, click the refresh arrow in the upper right corner.
  * If you are using the IBM Quantum channel, in IBM Quantum platform, open the `Jobs page <https://quantum-computing.ibm.com/jobs>`__.

Full example
------------

starts a session, runs an Estimator job, and outputs the result:

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
      estimator = Estimator(options=options)
      job = estimator.run(circuit, observable)
      result = job.result()
      # Close the session only if all jobs are finished, and you don't need to run more in the session
      session.close()

  display(circuit.draw("mpl"))
  print(f" > Observable: {observable.paulis}")
  print(f" > Expectation value: {result.values[0]}")
  print(f" > Metadata: {result.metadata[0]}")

*************************************************************************************



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


