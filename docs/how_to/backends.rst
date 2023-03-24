Run on quantum backends
=================================

A **backend** represents either a simulator or a real quantum computer and are responsible for running quantum circuits, running pulse schedules, and returning results.

In qiskit-ibm-runtime, a backend is represented by an instance of the ``IBMBackend`` class. Attributes of this class provides information about this backend. For example:

* ``name``: Name of the backend.
* ``instructions``: A list of instructions the backend supports.
* ``operation_names``: A list of instruction names the backend supported.
* ``num_qubits``: The number of qubits the backend has.
* ``coupling_map``: Coupling map of the backend.
* ``dt``: System time resolution of input signals.
* ``dtm``: System time resolution of output signals.

Refer to the `API reference <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.IBMBackend.html#qiskit_ibm_runtime.IBMBackend>`__ for a complete list of attributes and methods.

Initialize the service
------------------------

Before calling ``IBMBackend``, initialize the service:

.. code-block:: python

  from qiskit_ibm_runtime import QiskitRuntimeService

  # Initialize the account first.
  service = QiskitRuntimeService()

List backends
-------------

Use the ``backends()`` method to list all backends you have access to. This method returns a list of ``IBMBackend`` instances:

.. code-block:: python

  service.backends()

.. code-block::

  [<IBMBackend('ibmq_qasm_simulator')>,
  <IBMBackend('simulator_stabilizer')>,
  <IBMBackend('simulator_mps')>,
  <IBMBackend('simulator_extended_stabilizer')>,
  <IBMBackend('simulator_statevector')>]  

The ``backend()`` (note that this is singular: *backend*) method takes the name of the backend as the input parameter and returns an ``IBMBackend`` instance representing that particular backend:

.. code-block:: python

  service.backend("ibmq_qasm_simulator")

.. code-block::

  <IBMBackend('ibmq_qasm_simulator')>  


Filter backends
----------------

You may also optionally filter the set backends, by passing arguments that query the backend's configuration, status, or properties. For more general filters, you can make advanced functions using a lambda function. Refer to the API documentation for more details.

Let's try getting only backends that fit these criteria:

* Are real quantum devices (``simulator=False``)
* Are currently operational (``operational=True``)
* Have at least 5 qubits (``min_num_qubits=5``)

.. code-block:: python

  service.backends(simulator=False, operational=True, min_num_qubits=5)

A similar method is ``least_busy()``, which takes the same filters as ``backends()`` but returns the backend that matches the filters and has the least number of jobs pending in the queue:

.. code-block:: python

  service.least_busy(operational=True, min_num_qubits=5)

Some programs also define the type of backends they need in the ``backend_requirements`` field of the program metadata.

The hello-world program, for example, needs a backend that has at least 5 qubits:

.. code-block:: python
  
  ibm_quantum_service = QiskitRuntimeService(channel="ibm_quantum")
  program = ibm_quantum_service.program("hello-world")
  print(program.backend_requirements)

.. code-block::

  {'min_num_qubits': 5}

After determining the backend requirements, you can find backends that meet the criteria:

.. code-block:: python

  ibm_quantum_service.backends(min_num_qubits=5)


Determine backend attributes
-------------------------------------

As mentioned previously, the ``IBMBackend`` class attributes provide information about the backend.  For example: 

.. code-block:: python
  
  backend = service.backend("ibmq_qasm_simulator")
  backend.name #returns the backend's name
  backend.backend_version #returns the version number
  backend.simulator #returns True or False, depending on whether it is a simulator
  backend.num_qubits #returns the number of qubits the backend has

.. vale IBMQuantum.Spelling = NO

See the `IBMBackend class documentation <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.IBMBackend.html#qiskit_ibm_runtime.IBMBackend>`__ for the full list of backend attributes.  

.. vale IBMQuantum.Spelling = YES

Find backend information from other channels
--------------------------------------------------

To find your available systems and simulators on **IBM Cloud**, view the `Compute resources page <https://cloud.ibm.com/quantum/resources/your-resources>`__. You must be logged in to see your available compute resources. You are shown a snapshot of each backend.  To see full details, click the backend name. You can also search for backends from this page.

To find your available systems and simulators on **IBM Quantum Platform**, view the `Compute resources page <https://quantum-computing.ibm.com/services/resources>`__. You are shown a snapshot of each backend.  To see full details, click the backend name. You can also sort, filter, and search from this page. 

Specify a backend when running a job
---------------------------------------

To specify a backend when running a job, add the ``backend`` option when starting your session. For details about working with sessions, see `Run a primitive in a session <run_session.html>`__.

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
       session.close() # Closes the session

  display(circuit.draw("mpl"))
  print(f" > Observable: {observable.paulis}")
  print(f" > Expectation value: {result.values[0]}")
  print(f" > Metadata: {result.metadata[0]}")
