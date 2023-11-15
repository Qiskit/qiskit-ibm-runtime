Migration guide: Migrate ``backend.run()`` from ``qiskit_ibm_provider`` to ``qiskit_ibm_runtime``
=================================================================================================

The Qiskit Runtime interface includes two packages:
Qiskit IBM Provider (the ``qiskit_ibm_provider`` package) and
Qiskit IBM Runtime (the ``qiskit_ibm_runtime`` package). Until now,
primitives (``Sampler`` and ``Estimator``)
were run in Runtime. Custom circuits that performed their own transpilation and used ``IBMBackend.run()``
were run in Provider.

In this release, we add support for running custom circuits using ``IBMBackend.run()`` in Runtime,
so users can run all programs through Runtime.

This guide describes how to migrate code that implemented ``IBMBackend.run()``
using Qiskit IBM Provider to use Qiskit IBM Runtime instead.

**Example 1: Straightforward execution of IBMBackend.run()**

.. code-block:: python

    from qiskit import *
    from qiskit.compiler import transpile, assemble
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()

In Provider, the code is:

.. code-block:: python

    from qiskit_ibm_provider import IBMProvider
    provider = IBMProvider()
    backend = provider.get_backend("ibmq_qasm_simulator")
    transpiled_circuit = transpile(circuit, backend=backend)
    job = backend.run(transpiled_circuit)
    print(job.result())

In Runtime, the code is:

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")
    transpiled_circuit = transpile(circuit, backend=backend)
    job = backend.run(transpiled_circuit)
    print(job.result())

**Example 2: Execution of backend.run() within a session:**

This section of code is identical in Provider and in Runtime.

.. code-block:: python

    with backend.open_session() as session:
        job1 = backend.run(transpiled_circuit)
        job2 = backend.run(transpiled_circuit)
        print(job1.session_id)
        print(job2.session_id)
    backend.cancel_session()

Sessions are implemented differently in ``IBMBackend`` than when using primitives.
Therefore, we cannot run a primitive and a backend using a single session. This will be remediated
in subsequent releases.

**Example 3: Primitive session containing backend.run:**

In this example, ``sampler`` is run within session, but ``backend`` is run independently
of the session.

.. code-block:: python

    from qiskit_ibm_runtime import Session, Sampler
    with Session(backend=backend) as session:
        sampler = Sampler(session=session)
        job1 = sampler.run(transpiled_circuit)
        job2 = backend.run(transpiled_circuit) # runs outside the session
        print(job1.session_id)
        print(job2.session_id)  # is None

**Example 4: Backend session containing Sampler:**

In this example, ``backend`` is run within a session, but ``sampler`` is run independently
of the session.

.. code-block:: python

    with backend.open_session() as session:
        sampler = Sampler(backend=backend)
        job1 = sampler.run(transpiled_circuit)  # runs outside the session
        job2 = backend.run(transpiled_circuit)
        session_id = session.session_id
        print(job1.session_id)  # is None
        print(job2.session_id)


