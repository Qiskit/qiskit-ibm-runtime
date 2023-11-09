.. _migrate to primitives:

Migration guide: using ``backend.run()`` in ``qiskit_ibm_runtime``
==================================================================

This guide describes how to migrate code that implemented ``backend.run()``
using Qiskit IBM Provider (the ``qiskit_ibm_provider`` package) to code using the
Qiskit IBM Runtime (``qiskit_ibm_runtime`` package).
We demonstrate the migration with code examples.

**Example 1: Straightforward execution of ``backend.run()``**

.. code-block:: python

    from qiskit import *
    from qiskit.compiler import transpile, assemble
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    transpiled_circuit = transpile(circuit, backend=backend)

In the Provider, the code is:

.. code-block:: python

    from qiskit_ibm_provider import IBMProvider
    provider = IBMProvider()
    backend = provider.get_backend("ibmq_qasm_simulator")
    job = backend.run(transpiled_circuit)
    print(job.result())

In Runtime, the code will be:

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitIBMService()
    backend = service.backend("ibmq_qasm_simulator")
    job = backend.run(transpiled_circuit)
    print(job.result())

**Example 2: Execution of ``backend.run()`` within a session:**

This section of code is identical in Provider and in Runtime.

.. code-block:: python

    with backend.open_session() as session:
        job1 = backend.run(transpiled_circuit)
        job2 = backend.run(transpiled_circuit)

The Session for ``Primitives`` (``Sampler`` and ``Estimator``) is currently different than
the Session for ``IBMBackend``. Therefore, we cannot run a primitive and a backend
using a single Session.

**Example 3: Primitive Session containing ``backend.run``:**

In this example, ``sampler`` is run within session, but ``backend`` is run independently
of ``session``.

.. code-block:: python

    with Session(backend=backend) as session:
        sampler = Sampler(session=session)
        job1 = sampler.run(transpiled_circuit)
        job2 = backend.run(transpiled_circuit)

**Example 4: Backend Session containing ``Sampler``:**

In this example, ``backend`` is run within a session, but ``sampler` is run independently
of ``session``.

.. code-block:: python

    with backend.open_session() as session:
        sampler = Sampler(backend=backend)
        job1 = backend.run(transpiled_circuit)
        job2 = sampler.run(transpiled_circuit)
        session_id = session.session_id
