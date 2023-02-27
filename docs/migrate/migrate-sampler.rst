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

.. |QuasiDistribution.binary_probabilities| replace:: ``QuasiDistribution.binary_probabilities()``
.. _QuasiDistribution.binary_probabilities: https://qiskit.org/documentation/stubs/qiskit.result.QuasiDistribution.binary_probabilities.html#qiskit.result.QuasiDistribution.binary_probabilities


The role of the ``Sampler`` primitive is two-fold: it acts as an **entry point** to the quantum devices or
simulators, replacing ``backend.run()``. Additionally, it is an **algorithmic abstraction**
for the extraction of probability distributions from measurement counts.

They both take in circuits as inputs, bue the main difference between the former and the latter is the format of the
output: ``backend.run()`` outputs **counts**, while the ``Sampler`` processes those counts and outputs
the **quasi-probability distribution** associated with them.


.. note::

    **Backend.run() model:** In this model, you accessed real backends and remote simulators using the
    ``qiskit-ibmq-provider`` module (now migrated to ``qiskit-ibm-provider``). If you wanted to run
    **local** simulations, you could import a specific backend from ``qiskit-aer``. All of them followed
    the ``backend.run()`` interface.

    This guide will use the now deprecated ``qiskit-ibmq-provider`` syntax for the legacy code examples.
    For more information in how to migrate to the new ``qiskit-ibm-provider``, please read the following
    `provider migration guide <https://github.com/Qiskit/qiskit-ibm-provider/blob/main/docs/tutorials/Migration_Guide_from_qiskit-ibmq-provider.ipynb>`_.

        .. raw:: html

            <details>
            <summary><a>Code Example for <code>qiskit-ibmq-provider</code> + <code>backend.run()</code></a></summary>
            <br>

        .. code-block:: python

            from qiskit import IBMQ

            # Select provider
            provider = IBMQ.load_account()

            # Get backend
            backend = provider.get_backend("ibmq_qasm_simulator") # cloud simulator

            # Run
            result = backend.run(circuits)

        .. raw:: html

            </details>
            <br>

        .. raw:: html

            <details>
            <summary><a>Code Example for <code>qiskit-aer</code> + <code>backend.run()</code> </a></summary>
            <br>

        .. code-block:: python

            from qiskit_aer import AerSimulator # former import: from qiskit import Aer

            # Get local simulator backend
            backend = AerSimulator()

            # Run
            result = backend.run(circuits)

        .. raw:: html

            </details>
            <br>

    **Primitives model:** You access real backends and remote simulators through the `qiskit-ibm-runtime`
    **primitives** (`Sampler` and `Estimator`). If you want to run **local** simulations, you can import specific `local` primitives
    from |qiskit_aer.primitives|_ and |qiskit.primitives|_. All of them follow the |BaseSampler|_ and |BaseEstimator|_ interfaces, but
    **only the Runtime primitives offer access to the Runtime service, sessions, and built-in error mitigation**.

        .. raw:: html

            <details>
            <summary><a>Code Example for Runtime Sampler</a></summary>
            <br>

        .. code-block:: python

            from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

            # Define service
            service = QiskitRuntimeService()

            # Get backend
            backend = service.backend("ibmq_qasm_simulator") # cloud simulator

            # Define Sampler
            # (see tutorials more more info on sessions)
            sampler = Sampler(session=backend)

            # Run Quasi-Probability calculation
            result = sampler.run(circuits).result()

        .. raw:: html

            </details>
            <br>

        .. raw:: html

            <details>
            <summary><a>Code Example for Aer Estimator</a></summary>
            <br>

        .. code-block:: python

            from qiskit_aer import Sampler

            # Get local simulator Sampler
            sampler = Sampler()

            # Run Quasi-Probability calculation
            result = sampler.run(circuits).result()

        .. raw:: html

            </details>
            <br>

Let's see how to sample a circuit with ``backend.run()`` and using the ``Sampler``.

End-to-end example
------------------

1. Problem definition
----------------------

We want to find out the probability (or quasi-probability) distribution associated to a quantum state:

.. attention::

    Careful with the measurements!!! If you want to use the ``Sampler`` primitive, the circuit
    **must contain measurements**.

.. code-block:: python

    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(4)
    circuit.h(range(2))
    circuit.cx(0,1)
    circuit.measure_all() # measurement!!!

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

    from qiskit import IBMQ

    # Define provider and backend
    provider = IBMQ.load_account()
    backend = provider.get_backend("ibmq_qasm_simulator")

    # Run
    result = backend.run(circuit, shots=1024).result()

.. code-block:: python

    >>> print("result: ", result)
    result:  Result(backend_name='ibmq_qasm_simulator', backend_version='0.11.0',
    qobj_id='65bb8a73-cced-40c1-995a-8961cc2badc4', job_id='63fc95612751d57b6639f777',
    success=True, results=[ExperimentResult(shots=1024, success=True, meas_level=2,
    data=ExperimentResultData(counts={'0x0': 255, '0x1': 258, '0x2': 243, '0x3': 268}),
    header=QobjExperimentHeader(clbit_labels=[['meas', 0], ['meas', 1], ['meas', 2], ['meas', 3]],
    creg_sizes=[['meas', 4]], global_phase=0.0, memory_slots=4, metadata={}, n_qubits=4,
    name='circuit-930', qreg_sizes=[['q', 4]], qubit_labels=[['q', 0], ['q', 1], ['q', 2], ['q', 3]]),
    status=DONE, metadata={'active_input_qubits': [0, 1, 2, 3], 'batched_shots_optimization': False,
    'device': 'CPU', 'fusion': {'enabled': False}, 'input_qubit_map': [[3, 3], [2, 2], [1, 1], [0, 0]],
    'measure_sampling': True, 'method': 'stabilizer', 'noise': 'ideal', 'num_clbits': 4, 'num_qubits': 4,
    'parallel_shots': 1, 'parallel_state_update': 16, 'remapped_qubits': False,
    'sample_measure_time': 0.001001096}, seed_simulator=2191402198, time_taken=0.002996865)],
    date=2023-02-27 12:35:00.203255+01:00, status=COMPLETED, header=QobjHeader(backend_name='ibmq_qasm_simulator',
    backend_version='0.1.547'), metadata={'max_gpu_memory_mb': 0, 'max_memory_mb': 386782, 'mpi_rank': 0,
    'num_mpi_processes': 1, 'num_processes_per_experiments': 1, 'omp_enabled': True, 'parallel_experiments': 1,
    'time_taken': 0.003215252, 'time_taken_execute': 0.00303248, 'time_taken_load_qobj': 0.000169435},
    time_taken=0.003215252, client_version={'qiskit': '0.39.5'})

Now let's get the probability distribution from the output:

.. code-block:: python

    counts = result.get_counts(circuit)
    quasi_dists = {}
    for key,count in counts.items():
        quasi_dists[key] = count/1024

.. code-block:: python

    >>> print("counts: ", counts)
    >>> print("quasi_dists: ", quasi_dists)
    counts:  {'0000': 255, '0001': 258, '0010': 243, '0011': 268}
    quasi_dists:  {'0000': 0.2490234375, '0001': 0.251953125, '0010': 0.2373046875, '0011': 0.26171875}


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

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{0: 0.2802734375, 1: 0.2509765625, 2: 0.232421875, 3: 0.236328125}],
    metadata=[{'header_metadata': {}, 'shots': 1024, 'readout_mitigation_overhead': 1.0,
    'readout_mitigation_time': 0.03801989182829857}])
    quasi_dists:  [{0: 0.2802734375, 1: 0.2509765625, 2: 0.232421875, 3: 0.236328125}]

.. attention::

    Careful with the output format!!! With the ``Sampler`` the states are now longer represented
    with bitstrings (i.e ``"11"``\),
    but integers (i.e ``3``\). If you want to convert the ``Sampler``\'s output to bitstrings,
    you can use the |QuasiDistribution.binary_probabilities|_ method as shown below.

.. code-block:: python

    >>> # convert output to bitstrings
    >>> binary_quasi_dist = quasi_dists[0].binary_probabilities()
    >>> print("binary_quasi_dist: ", binary_quasi_dist)
    binary_quasi_dist:  {'0000': 0.2802734375, '0001': 0.2509765625, '0010': 0.232421875, '0011': 0.236328125}

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
    result:  Result(backend_name='aer_simulator_statevector', backend_version='0.11.2',
    qobj_id='e51e51bc-96d8-4e10-aa4e-15ee6264f4a0', job_id='c603daa7-2c03-488c-8c75-8c6ea0381bbc',
    success=True, results=[ExperimentResult(shots=1024, success=True, meas_level=2,
    data=ExperimentResultData(counts={'0x2': 236, '0x0': 276, '0x3': 262, '0x1': 250}),
    header=QobjExperimentHeader(clbit_labels=[['meas', 0], ['meas', 1], ['meas', 2], ['meas', 3]],
    creg_sizes=[['meas', 4]], global_phase=0.0, memory_slots=4, metadata={}, n_qubits=4, name='circuit-930',
    qreg_sizes=[['q', 4]], qubit_labels=[['q', 0], ['q', 1], ['q', 2], ['q', 3]]), status=DONE,
    seed_simulator=3531074553, metadata={'parallel_state_update': 16, 'parallel_shots': 1,
    'sample_measure_time': 0.000405246, 'noise': 'ideal', 'batched_shots_optimization': False,
    'remapped_qubits': False, 'device': 'CPU', 'active_input_qubits': [0, 1, 2, 3], 'measure_sampling': True,
    'num_clbits': 4, 'input_qubit_map': [[3, 3], [2, 2], [1, 1], [0, 0]], 'num_qubits': 4, 'method': 'statevector',
    'fusion': {'applied': False, 'max_fused_qubits': 5, 'threshold': 14, 'enabled': True}}, time_taken=0.001981756)],
    date=2023-02-27T12:38:18.580995, status=COMPLETED, header=QobjHeader(backend_name='aer_simulator_statevector',
    backend_version='0.11.2'), metadata={'mpi_rank': 0, 'num_mpi_processes': 1, 'num_processes_per_experiments': 1,
    'time_taken': 0.002216379, 'max_gpu_memory_mb': 0, 'time_taken_execute': 0.002005713, 'max_memory_mb': 65536,
    'time_taken_load_qobj': 0.000200642, 'parallel_experiments': 1, 'omp_enabled': True},
    time_taken=0.0025920867919921875)

Now let's get the probability distribution from the output:

.. code-block:: python

    counts = result.get_counts(circuit)
    quasi_dists = {}
    for key,count in counts.items():
        quasi_dists[key] = count/1024

.. code-block:: python

    >>> print("counts: ", counts)
    >>> print("quasi_dists: ", quasi_dists)
    counts:  {'0010': 236, '0000': 276, '0011': 262, '0001': 250}
    quasi_dists:  {'0010': 0.23046875, '0000': 0.26953125, '0011': 0.255859375, '0001': 0.244140625}

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
    result:  SamplerResult(quasi_dists=[{0: 0.249999999999, 1: 0.249999999999,
    2: 0.249999999999, 3: 0.249999999999}], metadata=[{}])
    quasi_dists:  [{0: 0.249999999999, 1: 0.249999999999, 2: 0.249999999999,
    3: 0.249999999999}]

If shots are specified, this primitive outputs a shot-based simulation (no longer exact):

.. code-block:: python

    from qiskit.primitives import Sampler

    sampler = Sampler()

    result = sampler.run(circuit, shots=1024).result()
    quasi_dists = result.quasi_dists

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{0: 0.2490234375, 1: 0.2578125,
    2: 0.2431640625, 3: 0.25}], metadata=[{'shots': 1024}])
    quasi_dists:  [{0: 0.2490234375, 1: 0.2578125, 2: 0.2431640625, 3: 0.25}]

You can still access the Aer Simulator through its dedicated
``Sampler``. This can be handy for performing simulations with noise models. In this example,
the simulation method has been fixed to match the result from 3.a.

.. code-block:: python

    from qiskit_aer.primitives import Sampler as AerSampler # import change!!!

    sampler = AerSampler(run_options= {"method": "statevector"})

    result = sampler.run(circuit, shots=1024).result()
    quasi_dists = result.quasi_dists

.. code-block:: python

    >>> print("result: ", result)
    >>> print("quasi_dists: ", quasi_dists)
    result:  SamplerResult(quasi_dists=[{1: 0.2802734375, 2: 0.2412109375, 0: 0.2392578125,
    3: 0.2392578125}], metadata=[{'shots': 1024, 'simulator_metadata':
    {'parallel_state_update': 16, 'parallel_shots': 1, 'sample_measure_time': 0.000409608,
    'noise': 'ideal', 'batched_shots_optimization': False, 'remapped_qubits': False,
    'device': 'CPU', 'active_input_qubits': [0, 1, 2, 3], 'measure_sampling': True,
    'num_clbits': 4, 'input_qubit_map': [[3, 3], [2, 2], [1, 1], [0, 0]], 'num_qubits': 4,
    'method': 'statevector', 'fusion': {'applied': False, 'max_fused_qubits': 5,
    'threshold': 14, 'enabled': True}}}])
    quasi_dists:  [{1: 0.2802734375, 2: 0.2412109375, 0: 0.2392578125, 3: 0.2392578125}]

.. code-block:: python

    >>> # convert output to bitstrings
    >>> binary_quasi_dist = quasi_dists[0].binary_probabilities()
    >>> print("binary_quasi_dist: ", binary_quasi_dist)
    binary_quasi_dist:  {'0001': 0.2802734375, '0010': 0.2412109375, '0000': 0.2392578125, '0011': 0.2392578125}

For more information on running noisy simulations with the **Runtime Primitives**, you can see this
`topic <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/noisy_simulators.html>`_.