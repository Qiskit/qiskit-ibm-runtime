.. _migrate to primitives:

Migration guide: using ``backend.run()`` in ``qiskit_ibm_runtime``
==================================================================

This guide describes how to migrate code that was implemented ``backend.run()``
using Qiskit IBM Provider (the ``qiskit_ibm_provider`` package) to code using the
Qiskit IBM Runtime (``qiskit_ibm_runtime`` package).
We demonstrate the migration with code examples.

Example 1: Straightforward execution of ``backend.run()``

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

Example 2: Execution of ``backend.run()`` within a session:

.. code-block:: python

     with backend.open_session() as session:
        job1 = backend.run(transpiled_circuit)
        job2 = backend.run(transpiled_circuit)

This section of code is identical in Provider and in Runtime.

Related links
-------------

* `Get started with Estimator <../tutorials/how-to-getting-started-with-estimator.ipynb>`__
* `Get started with Sampler <../tutorials/how-to-getting-started-with-sampler.ipynb>`__
* `Tutorial: Migrate from qiskit-ibmq-provider to qiskit-ibm-provider <https://qiskit.org/documentation/partners/qiskit_ibm_provider/tutorials/Migration_Guide_from_qiskit-ibmq-provider.html>`__
