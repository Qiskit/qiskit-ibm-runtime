Circuit sampling in an algorithm
=================================

In the case of circuit sampling, the Sampler primitive acts as a direct replacement of `backend.run()` or `QuantumInstance` with additional capabilities, such as error mitigation. The main difference between the former and the latter is the format of the output. Backend.run outputs **counts**, while Sampler processes those counts and outputs  the **quasi-probability distribution** associated with them.

Let's see how to sample a circuit with the legacy code and using the primitives:

Problem definition 
---------------------------

We want to measure a quantum state:

.. code-block:: python

    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(2)
    circuit.x(0)
    circuit.x(1)
    circuit.measure_all()

Option 1: Run locally 
~~~~~~~~~~~~~~~~~~~~~~~~
.. raw:: html

    <details>
    <summary><a>Legacy method</a></summary>

.. code-block:: python

    from qiskit import Aer, transpile

    # Transpile for simulator
    simulator = Aer.get_backend('aer_simulator')

    # Run and get counts
    result = simulator.run(circuit, shots=1024).result()
    counts = result.get_counts(circuit)
    print(counts)
    
    # Get quasi prob. distribution
    quasi_dists = {}
    for key,count in counts.items():
        quasi_dists[key] = count/1024
    print(quasi_dists)

.. raw:: html

   </details>

.. raw:: html

    <details>
    <summary><a>New method</a></summary>

This can be done with the reference sampler in `qiskit.primitives` (exact statevector calculation):

.. code-block:: python

    from qiskit.primitives import Sampler

    sampler = Sampler()

    result = sampler.run(circuit).result().quasi_dists
    print(result)

If shots are specified, this primitive outputs a shot-based simulation (no longer exact):

.. code-block:: python

    from qiskit.primitives import Sampler

    sampler = Sampler()

    result = sampler.run(circuit, shots = 1024).result().quasi_dists
    print(result)

.. raw:: html

   </details>    


Option 2: Run on a remote simulator or real backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. raw:: html

    <details>
    <summary><a>Legacy method</a></summary>

.. code-block:: python

    from qiskit import IBMQ

    IBMQ.load_account()
    provider = IBMQ.get_provider(hub='ibm-q-internal') # here the hub should not be internal
    backend = provider.get_backend("ibmq_qasm_simulator")

    # Run and get counts
    result = simulator.run(circuit, shots=1024).result()
    counts = result.get_counts(circuit)
    print(counts)
    
    # Get quasi prob. distribution
    quasi_dists = {}
    for key,count in counts.items():
        quasi_dists[key] = count/1024
    print(quasi_dists)

    # The quantum instance example is analogous to option 1.

.. raw:: html

   </details>

.. raw:: html

    <details>
    <summary><a>New method</a></summary>

.. code-block:: python
    
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")

    sampler = Sampler(session=backend)

    result = sampler.run(circuit, shots=1024).result().quasi_dists
    print(result)

.. raw:: html

   </details>   