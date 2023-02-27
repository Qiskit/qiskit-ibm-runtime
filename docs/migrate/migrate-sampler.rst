Circuit sampling in an algorithm
=================================

Background
----------

.. |qiskit.opflow| replace:: ``qiskit.opflow``
.. _qiskit.opflow: https://qiskit.org/documentation/apidoc/opflow.html

.. |BaseEstimator| replace:: ``BaseEstimator``
.. _BaseEstimator: https://qiskit.org/documentation/stubs/qiskit.primitives.BaseEstimator.html

.. |BaseSampler| replace:: ``BaseSampler``
.. _BaseSampler: https://qiskit.org/documentation/stubs/qiskit.primitives.BaseSampler.html

.. |qiskit_aer.primitives| replace:: ``qiskit_aer.primitives``
.. _qiskit_aer.primitives: https://github.com/Qiskit/qiskit-aer/tree/main/qiskit_aer/primitives

.. |qiskit.primitives| replace:: ``qiskit.primitives``
.. _qiskit.primitives: https://qiskit.org/documentation/apidoc/primitives.html



The role of the ``Sampler`` primitive is two-fold: on one hand, it acts as an entry point to the quantum devices or
simulators, replacing ``backend.run()``. On the other hand, it is an **algorithmic abstraction** for the calculation
of probability distributions extracted from measurement counts.

They both take in circuits as inputs, bue he main difference between the former and the latter is the format of the
output: ``backend.run()`` outputs **counts**, while the ``Sampler`` processes those counts and outputs
the **quasi-probability distribution** associated with them.

.. note::

    **Backend.run() model:** You could access real backends and remote simulators through the ``qiskit_ibm_provider``
    module. If you wanted to run **local** simulations, you could import a specific backend
    from ``qiskit_aer``. All of them followed the ``backend.run()`` interface.

    .. raw:: html

        <details>
        <summary><a>Code Examples</a></summary>
        <br>

    .. code-block:: python

        from qiskit_ibm_provider import IBMProvider # former import: from qiskit import IBMQ
        # define provider and backend
        provider = IBMProvider()
        backend = provider.get_backend("ibmq_qasm_simulator") # cloud simulator
        ...
        result = backend.run(circuits)

    .. code-block:: python

        from qiskit_aer import AerSimulator # former import: from qiskit import Aer
        # define local simulation method
        backend = AerSimulator()
        ...
        result = backend.run(circuits)

    .. raw:: html

        </details>
        <br>

    **Primitives model:** You can access real backends and remote simulators through the ``qiskit_ibm_runtime``
    **primitives** (``Sampler``, ``Estimator``). If you want to run **local** simulations, you can import specific local primitives
    from |qiskit_aer.primitives|_ and |qiskit.primitives|_. All of them follow the |BaseSampler|_ and |BaseEstimator|_ interfaces, but
    **only the Runtime Primitives offer access to the Runtime service, sessions, and built-in error mitigation**.

    .. raw:: html

        <details>
        <summary><a>Code Examples</a></summary>
        <br>

    .. code-block:: python

        from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
        # define service and backend
        service = QiskitRuntimeService()
        backend = service.backend("ibmq_qasm_simulator") # cloud simulator
        # see tutorials more more info on sessions
        sampler = Sampler(session=backend)
        ...
        result = sampler.run(circuits, observables).result()

    .. code-block:: python

        from qiskit_aer import Sampler as AerSampler
        # the Aer primitive's backend is fixed to the Aer Simulator
        sampler = AerSampler()
        ...
        result = sampler.run(circuits, observables).result()

    .. code-block:: python

        from qiskit import Sampler as ReferenceSampler
        # the Qiskit reference primitives' backend is fixed to a Statevector simulator
        sampler = ReferenceSampler()
        ...
        result = sampler.run(circuits, observables).result()

    .. raw:: html

        </details>
        <br>

Let's see how to sample a circuit with ``backend.run()`` and using the ``Sampler``.

End-to-end example
------------------

1. Define problem
~~~~~~~~~~~~~~~~~~

We want to find out the probability (or quasi-probability) distribution associated to a quantum state:

.. code-block:: python

    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(2)
    circuit.x(0)
    circuit.x(1)
    circuit.measure_all()

2. Calculate probability distribution on real device or cloud simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

2.a. [Legacy] Using ``backend.run()``
#####################################

.. note::

    You can replace ``ibmq_qasm_simulator`` with your device name to see the
    complete workflow for a real device.

.. code-block:: python

    from qiskit_ibm_provider import IBMProvider

    # Define provider and backend
    provider = IBMProvider()
    backend = provider.get_backend("ibmq_qasm_simulator")

    # Run
    result = backend.run(circuit, shots=1024).result()

.. code-block:: python

    >>> print("result: ", result)
    result: Result(backend_name='qasm_simulator', backend_version='0.11.2',
    qobj_id='29fb4c00-1d88-4275-b5f2-289e191ccb30',
    job_id='3228877b-f478-49f8-8811-70912aa3163e',
    success=True, results=[ExperimentResult(shots=1024, success=True, meas_level=2,
    data=ExperimentResultData(counts={'0x3': 1024}),
    header=QobjExperimentHeader(clbit_labels=[['meas', 0],
    ['meas', 1]], creg_sizes=[['meas', 2]],
    global_phase=0.0, memory_slots=2, metadata={},
    n_qubits=2, name='circuit-925', qreg_sizes=[['q', 2]],
    qubit_labels=[['q', 0], ['q', 1]]), status=DONE, seed_simulator=1687731339,
    metadata={'parallel_state_update': 16, 'sample_measure_time': 0.001434541,
    'noise': 'ideal', 'batched_shots_optimization': False, 'measure_sampling': True,
    'device': 'CPU', 'num_qubits': 2, 'parallel_shots': 1, 'remapped_qubits': False,
    'method': 'stabilizer', 'active_input_qubits': [0, 1], 'num_clbits': 2,
    'input_qubit_map': [[1, 1], [0, 0]], 'fusion': {'enabled': False}},
    time_taken=0.005606335)], date=2023-02-24 16:36:20.889579+01:00,
    status=COMPLETED, header=QobjHeader(backend_name='qasm_simulator',
    backend_version='0.11.2'), metadata={'time_taken': 0.00604436,
    'time_taken_execute': 0.005678122, 'mpi_rank': 0, 'parallel_experiments': 1,
    'omp_enabled': True, 'max_gpu_memory_mb': 0, 'num_processes_per_experiments': 1,
    'num_mpi_processes': 1, 'time_taken_load_qobj': 0.00034589, 'max_memory_mb': 64216},
    time_taken=0.00669550895690918)

Now let's get the probability distribution from the output:

.. code-block:: python

    counts = result.get_counts(circuit)
    quasi_dists = {}
    for key,count in counts.items():
        quasi_dists[key] = count/1024

.. code-block:: python

    >>> print("counts: ", counts)
    >>> print("quasi_dists: ", quasi_dists)
    counts: {'11': 1024}
    quasi_dists: {'11': 1.0}


2.b. [New] Using Runtime ``Sampler``
###########################################

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")

    sampler = Sampler(session=backend)

    result = sampler.run(circuit, shots=1024).result()
    quasi_dists = result.quasi_dists

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{3: 1.0}], metadata=[{'header_metadata': {},
    'shots': 1024, 'readout_mitigation_overhead': 1.0,
    'readout_mitigation_time': 0.024925401899963617}])
    quasi_dists:  [{3: 1.0}]

3. Other execution alternatives (non-Runtime)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some cases, you might want to test your algorithm using local simulation. For this means, we
will show you two more migration paths using non-runtime primitives. Let's say that you want to
solve the problem defined above with a local statevector simulation.

3.a. [Legacy] Using Qiskit Aer's Simulator
###########################################


.. code-block:: python

    from qiskit_aer import AerSimulator

    # Define statevector simulator
    simulator = AerSimulator(method="statevector")

    # Run and get counts
    result = simulator.run(circuit, shots=1024).result()

.. code-block:: python

    >>> print("result: ", result)
    result: Result(backend_name='qasm_simulator', backend_version='0.11.2',
    qobj_id='29fb4c00-1d88-4275-b5f2-289e191ccb30',
    job_id='3228877b-f478-49f8-8811-70912aa3163e',
    success=True, results=[ExperimentResult(shots=1024, success=True, meas_level=2,
    data=ExperimentResultData(counts={'0x3': 1024}),
    header=QobjExperimentHeader(clbit_labels=[['meas', 0],
    ['meas', 1]], creg_sizes=[['meas', 2]],
    global_phase=0.0, memory_slots=2, metadata={},
    n_qubits=2, name='circuit-925', qreg_sizes=[['q', 2]],
    qubit_labels=[['q', 0], ['q', 1]]), status=DONE, seed_simulator=1687731339,
    metadata={'parallel_state_update': 16, 'sample_measure_time': 0.001434541,
    'noise': 'ideal', 'batched_shots_optimization': False, 'measure_sampling': True,
    'device': 'CPU', 'num_qubits': 2, 'parallel_shots': 1, 'remapped_qubits': False,
    'method': 'stabilizer', 'active_input_qubits': [0, 1], 'num_clbits': 2,
    'input_qubit_map': [[1, 1], [0, 0]], 'fusion': {'enabled': False}},
    time_taken=0.005606335)], date=2023-02-24 16:36:20.889579+01:00,
    status=COMPLETED, header=QobjHeader(backend_name='qasm_simulator',
    backend_version='0.11.2'), metadata={'time_taken': 0.00604436,
    'time_taken_execute': 0.005678122, 'mpi_rank': 0, 'parallel_experiments': 1,
    'omp_enabled': True, 'max_gpu_memory_mb': 0, 'num_processes_per_experiments': 1,
    'num_mpi_processes': 1, 'time_taken_load_qobj': 0.00034589, 'max_memory_mb': 64216},
    time_taken=0.00669550895690918)

Now let's get the probability distribution from the output:

.. code-block:: python

    counts = result.get_counts(circuit)
    quasi_dists = {}
    for key,count in counts.items():
        quasi_dists[key] = count/1024

.. code-block:: python

    >>> print("counts: ", counts)
    >>> print("quasi_dists: ", quasi_dists)
    counts: {'11': 1024}
    quasi_dists: {'11': 1.0}

3.b. [New] Using Reference ``Sampler`` or Aer ``Sampler``
##############################################################

The Reference ``Sampler`` allows to perform either an exact or a shot-based noisy simulation based
on the ``Statevector`` class in the ``qiskit.quantum_info`` module.

.. code-block:: python

    from qiskit.primitives import Sampler

    sampler = Sampler()

    quasi_dists = sampler.run(circuit).result().quasi_dists

.. code-block:: python

    >>> print("quasi_dists: ", quasi_dists)
    quasi_dists:  [{3: 1.0}]

If shots are specified, this primitive outputs a shot-based simulation (no longer exact):

.. code-block:: python

    from qiskit.primitives import Sampler

    sampler = Sampler()

    quasi_dists = sampler.run(circuit, shots = 1024).result().quasi_dists

.. code-block:: python

    >>> print("quasi_dists: ", quasi_dists)
    quasi_dists:  [{3: 1.0}]

You can still access the Aer Simulator through its dedicated
``Sampler``. This can come in handy for performing simulations with noise models. In this example,
the simulation method has been fixed to match the result from 3.a.

.. code-block:: python

    from qiskit_aer.primitives import Sampler as AerSampler # all that changes is the import!!!

    sampler = AerSampler(run_options= {"method": "statevector"})

    result = sampler.run(state, op).result().values

    # for shot-based simulation:
    expectation_value = sampler.run(state, op, shots=100).result().values

.. code-block:: python

    >>> print("quasi_dists: ", quasi_dists)
    quasi_dists:  [{3: 1.0}]
