Circuit sampling in an algorithm
=================================

The Sampler primitive is used to design an algorithm that samples circuits and extracts probability distributions.

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


The role of the ``Sampler`` primitive is two-fold: it acts as an **entry point** to quantum devices or
simulators, replacing ``backend.run()``. Additionally, it is an **algorithmic abstraction** to extract probability distributions from measurement counts.

Both ``Sampler`` and  ``backend.run()`` take in circuits as inputs. The main difference is the format of the
output: ``backend.run()`` outputs **counts**, while ``Sampler`` processes those counts and outputs
the **quasi-probability distribution** associated with them.


.. note::

    **Backend.run() model:** In this model, you used the
    ``qiskit-ibmq-provider`` (now migrated to ``qiskit-ibm-provider``) module to access real backends and remote simulators.
    To run **local** simulations, you could import a specific backend from ``qiskit-aer``. All of them followed
    the ``backend.run()`` interface.

        .. raw:: html

            <details>
            <summary><a>Code example with <code>qiskit-ibmq-provider</code> & <code>backend.run()</code></a></summary>
            <br>

        .. code-block:: python

            from qiskit import IBMQ

            # Select provider
            provider = IBMQ.load_account()

            # Get backend
            backend = provider.get_backend("ibmq_qasm_simulator") # Use the cloud simulator

            # Run
            result = backend.run(circuits)

        .. raw:: html

            </details>
            <br>

        .. raw:: html

            <details>
            <summary><a>Code example for <code>qiskit-aer</code> & <code>backend.run()</code> </a></summary>
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

    **Primitives model:** Access real backends and remote simulators through the `qiskit-ibm-runtime`
    **primitives** (`Sampler` and `Estimator`). To run **local** simulations, import specific `local` primitives
    from |qiskit_aer.primitives|_ and |qiskit.primitives|_. All of them follow the |BaseSampler|_ and |BaseEstimator|_ interfaces, but
    **only the Runtime primitives offer access to the Runtime service, sessions, and built-in error mitigation**.

        .. raw:: html

            <details>
            <summary><a>Code example for Runtime Sampler</a></summary>
            <br>

        .. code-block:: python

            from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

            # Define service
            service = QiskitRuntimeService()

            # Get backend
            backend = service.backend("ibmq_qasm_simulator") # Use a cloud simulator

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
            <summary><a>Code example for Aer Sampler</a></summary>
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

Next, we will show an end-to-end example of sampling a circuit: first, with ``backend.run()``, then by using the ``Sampler``.

End-to-end example
------------------


1. Problem definition
----------------------

We want to find the probability (or quasi-probability) distribution associated with a quantum state:

.. attention::

    Important: If you want to use the ``Sampler`` primitive, the circuit **must contain measurements**.

.. code-block:: python

    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(4)
    circuit.h(range(2))
    circuit.cx(0,1)
    circuit.measure_all() # measurement!

2. Calculate probability distribution on a real device or cloud simulator
-------------------------------------------------------------------------


2.a. [Legacy] Use ``backend.run()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The required steps to reach our goal with ``backend.run()`` are:

1. Run circuits
2. Get counts from the result object
3. Use the counts and shots to calculate the probability distribution


.. raw:: html

    <br>
    
First, we run the circuit in a cloud simulator and output the result object:

.. note::

    Replace ``ibmq_qasm_simulator`` with your device name to see the
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

Now we get the probability distribution from the output:

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


2.b. [New] Use the ``Sampler`` Runtime primitive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the user-side syntax of the ``Sampler`` is very similar to  ``backend.run()``, 
notice that the workflow is now simplified, as the quasi-probability distribution is returned
**directly** (no need to perform post-processing), together with some key metadata.

.. note::

    Replace ``ibmq_qasm_simulator`` with your device name to see the
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

    Be careful with the output format. With ``Sampler``, the states are no longer represented
    by bit strings, for example, ``"11"``, 
    but by integers, for example, ``3``. To convert the ``Sampler`` output to bit strings,
    you can use the |QuasiDistribution.binary_probabilities|_ method, as shown below.

.. code-block:: python

    >>> # convert the output to bit strings
    >>> binary_quasi_dist = quasi_dists[0].binary_probabilities()
    >>> print("binary_quasi_dist: ", binary_quasi_dist)
    binary_quasi_dist:  {'0000': 0.2802734375, '0001': 0.2509765625, '0010': 0.232421875, '0011': 0.236328125}

The ``Sampler`` Runtime primitive offers several features and tuning options that do not have a legacy alternative
to migrate from, but can help improve your performance and results. For more information, refer to the following:

- `Error mitigation tutorial <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/tutorials/Error-Suppression-and-Error-Mitigation.html>`_
- `Setting execution options topic <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/options.html>`_
- `How to run a session topic <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/run_session.html>`_


3. Other execution alternatives (non-Runtime)
---------------------------------------------

The following migration paths use non-Runtime primitives to use local simulation to test an algorithm. Let's assume that we want to use a local state vector simulation to solve the problem defined above.

3.a. [Legacy] Use the Qiskit Aer simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    from qiskit_aer import AerSimulator

    # Define the statevector simulator
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

3.b. [New] Use the Reference ``Sampler`` or Aer ``Sampler`` primitive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Reference ``Sampler`` lets you perform an exact or a shot-based noisy simulation based
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

You can still access the Aer simulator through its dedicated
``Sampler``. This can be handy for performing simulations with noise models. In this example,
the simulation method has been updated to match the result from 3.a.

.. code-block:: python

    from qiskit_aer.primitives import Sampler as AerSampler # import change!

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

    >>> # Convert the output to bit strings
    >>> binary_quasi_dist = quasi_dists[0].binary_probabilities()
    >>> print("binary_quasi_dist: ", binary_quasi_dist)
    binary_quasi_dist:  {'0001': 0.2802734375, '0010': 0.2412109375, '0000': 0.2392578125, '0011': 0.2392578125}

For information, see `Noisy simulators in Qiskit Runtime <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/noisy_simulators.html>`_.
