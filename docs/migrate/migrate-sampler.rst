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



The role of the ``Sampler`` primitive is two-fold: it acts as an **entry point** to the quantum devices or
simulators, replacing ``backend.run()``. Additionally, it is an **algorithmic abstraction**
for the extraction of probability distributions from measurement counts.

They both take in circuits as inputs, bue the main difference between the former and the latter is the format of the
output: ``backend.run()`` outputs **counts**, while the ``Sampler`` processes those counts and outputs
the **quasi-probability distribution** associated with them.

.. note::

    **Backend.run() model:** In this model, you accessed real backends and remote simulators through the ``qiskit_ibm_provider``
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

    **Primitives model:** You access real backends and remote simulators through the ``qiskit_ibm_runtime``
    **primitives** (``Sampler``, ``Estimator``). If you want to run **local** simulations, you can import specific `local` primitives
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

1. Problem definition
----------------------

We want to find out the probability (or quasi-probability) distribution associated to a quantum state:

.. code-block:: python

    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(2)
    circuit.x(0)
    circuit.x(1)
    circuit.measure_all()

2. Calculate probability distribution on real device or cloud simulator
-----------------------------------------------------------------------

2.a. [Legacy] Using ``backend.run()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The required steps to reach our goal with ``backend.run()`` are:

1. Execute circuits
2. Get counts from result object
3. Calculate probability distribution from counts and total number of shots

First, let's run the circuit in a cloud simulator and see the result object:

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


2.b. [New] Using the ``Sampler`` Runtime primitive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the user-side syntax if the ``Sampler`` is very similar to  ``backend.run()``, you can
notice that the workflow is now simplified, as the quasi-probability distribution is returned
**directly** (no need to perform post-processing), together with some key metadata.

.. note::

    You can replace ``ibmq_qasm_simulator`` with your device name to see the
    complete workflow for a real device.

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")

    sampler = Sampler(session=backend)

    result = sampler.run(circuit, shots=1024).result()
    quasi_dists = result.quasi_dists

.. attention::

    Pay attention to the output format, the states are now longer bitstrings (i.e ``\"11\"``\),
    but integers (i.e ``3``\).

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{3: 1.0}], metadata=[{'header_metadata': {},
    'shots': 1024, 'readout_mitigation_overhead': 1.0,
    'readout_mitigation_time': 0.024925401899963617}])
    quasi_dists:  [{3: 1.0}]

The ``Sampler`` Runtime primitive offers a series of features and tuning options that do not have a legacy alternative
to migrate from, but can help improve your performance and results. For more information, refer to the following:

- `Error mitigation tutorial <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/tutorials/Error-Suppression-and-Error-Mitigation.html>`_
- `Setting execution options topic <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/options.html>`_
- `Primitive execution options API reference <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.options.Options.html#qiskit_ibm_runtime.options.Options>`_
- `How to run a session topic <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/run_session.html>`_


3. Other execution alternatives (non-Runtime)
---------------------------------------------

You might want to test an algorithm using local simulation. We will next present other migration paths
using non-Runtime primitives to show how this can be done.

Let's assume that we want to solve the problem defined above with a local statevector simulation.

3.a. [Legacy] Using the Qiskit Aer simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    from qiskit_aer import AerSimulator

    # Define statevector simulator
    simulator = AerSimulator(method="statevector")

    # Run and get counts
    result = simulator.run(circuit, shots=1024).result()

.. code-block:: python

    >>> print("result: ", result)
    result: Result(backend_name='aer_simulator_statevector', backend_version='0.11.2',
    qobj_id='bf5ee881-bac9-4a3f-97ef-efd2fa2702e0', job_id='0c2b83f4-15ce-43ec-971f-bd591516c5c3',
    success=True, results=[ExperimentResult(shots=1024, success=True, meas_level=2,
    data=ExperimentResultData(counts={'0x3': 1024}), header=QobjExperimentHeader(clbit_labels=[['meas', 0],
    ['meas', 1]], creg_sizes=[['meas', 2]], global_phase=0.0, memory_slots=2, metadata={}, n_qubits=2,
    name='circuit-925', qreg_sizes=[['q', 2]], qubit_labels=[['q', 0], ['q', 1]]), status=DONE,
    seed_simulator=3084062053, metadata={'parallel_state_update': 16, 'parallel_shots': 1,
    'sample_measure_time': 0.000650894, 'noise': 'ideal', 'batched_shots_optimization': False,
    'remapped_qubits': False, 'device': 'CPU', 'active_input_qubits': [0, 1], 'measure_sampling': True,
    'num_clbits': 2, 'input_qubit_map': [[1, 1], [0, 0]], 'num_qubits': 2, 'method': 'statevector',
    'fusion': {'applied': False, 'max_fused_qubits': 5, 'threshold': 14, 'enabled': True}},
    time_taken=0.005783171)], date=2023-02-27T10:12:47.854046, status=COMPLETED,
    header=QobjHeader(backend_name='aer_simulator_statevector', backend_version='0.11.2'),
    metadata={'mpi_rank': 0, 'num_mpi_processes': 1, 'num_processes_per_experiments': 1,
    'time_taken': 0.011051999, 'max_gpu_memory_mb': 0, 'time_taken_execute': 0.006339488,
    'max_memory_mb': 65536, 'time_taken_load_qobj': 0.003530616, 'parallel_experiments': 1,
    'omp_enabled': True}, time_taken=0.04119110107421875)

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

3.b. [New] Using the Reference ``Sampler`` or Aer ``Sampler`` primitive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Reference ``Sampler`` lets you perform either an exact or a shot-based noisy simulation based
on the ``Statevector`` class in the ``qiskit.quantum_info`` module.

.. code-block:: python

    from qiskit.primitives import Sampler

    sampler = Sampler()

    result = sampler.run(circuit).result()
    quasi_dists = result.quasi_dists

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{3: 1.0}], metadata=[{}])
    quasi_dists:  [{3: 1.0}]

If shots are specified, this primitive outputs a shot-based simulation (no longer exact):

.. code-block:: python

    from qiskit.primitives import Sampler

    sampler = Sampler()

    result = sampler.run(circuit, shots=1024).result()
    quasi_dists = result.quasi_dists

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{3: 1.0}], metadata=[{'shots': 1024}])
    quasi_dists:  [{3: 1.0}]

You can still access the Aer Simulator through its dedicated
``Sampler``. This can be handy for performing simulations with noise models. In this example,
the simulation method has been fixed to match the result from 3.a.

.. code-block:: python

    from qiskit_aer.primitives import Sampler as AerSampler # all that changes is the import!!!

    sampler = AerSampler(run_options= {"method": "statevector"})

    result = sampler.run(circuit, shots=1024).result()
    quasi_dists = result.quasi_dists

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{3: 1.0}], metadata=[{'shots': 1024,
    'simulator_metadata': {'parallel_state_update': 16, 'parallel_shots': 1,
    'sample_measure_time': 0.000330278, 'noise': 'ideal', 'batched_shots_optimization': False,
    'remapped_qubits': False, 'device': 'CPU', 'active_input_qubits': [0, 1], 'measure_sampling': True,
    'num_clbits': 2, 'input_qubit_map': [[1, 1], [0, 0]], 'num_qubits': 2, 'method': 'statevector',
    'fusion': {'applied': False, 'max_fused_qubits': 5, 'threshold': 14, 'enabled': True}}}])
    quasi_dists:  [{3: 1.0}]


For more information on running noisy simulations with the **Runtime Primitives**, you can see this
`topic <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/noisy_simulators.html>`_.