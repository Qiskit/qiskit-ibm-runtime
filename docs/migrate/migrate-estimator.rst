Calculate expectation values in an algorithm
==============================================

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



The role of the ``Estimator`` primitive is two-fold: on one hand, it acts as an entry point to the quantum devices or
simulators, replacing ``backend.run()``. On the other hand, it is an **algorithmic abstraction** for expectation
value calculations, which removes the need
to perform operations to construct the final expectation circuit. This results in a considerable reduction of the code
complexity, and a more compact algorithm design.

.. note::

    **Backend.run() model:** You could access real backends and remote simulators through the ``qiskit_ibm_provider``
    module. If you wanted to run **local** simulations, you could import a specific backend
    from ``qiskit_aer``. All of them followed the ``backend.run()`` interface.

    .. raw:: html

        <details>
        <summary><a>Code Example</a></summary>
        <br>

    .. code-block:: python

        from qiskit_ibm_provider import IBMProvider # former import: from qiskit import IBMQ
        # define provider and backend
        provider = IBMProvider()
        backend = provider.get_backend("ibmq_qasm_simulator") # cloud simulator
        ...
        result = backend.run(circuits)

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
        <summary><a>Code Example</a></summary>
        <br>

    .. code-block:: python

        from qiskit_ibm_runtime import QiskitRuntimeService, Estimator
        # define service and backend
        service = QiskitRuntimeService()
        backend = service.backend("ibmq_qasm_simulator") # cloud simulator
        # see tutorials more more info on sessions
        estimator = Estimator(session=backend)
        ...
        result = estimator.run(circuits, observables).result()

        from qiskit_aer import Estimator as AerEstimator
        # the Aer primitive's backend is fixed to the Aer Simulator
        estimator = AerEstimator()
        ...
        result = estimator.run(circuits, observables).result()

        from qiskit import Estimator as ReferenceEstimator
        # the Qiskit reference primitives' backend is fixed to a Statevector simulator
        estimator = ReferenceEstimator()
        ...
        result = estimator.run(circuits, observables).result()

    .. raw:: html

        </details>
        <br>

If your code used to calculate expectation values using ``backend.run()``, you most likely used the |qiskit.opflow|_
module to handle operators and state functions. For this reason, the following migration example shows how to replace
the (|qiskit.opflow|_ + ``backend.run()``) workflow with an ``Estimator``-based workflow.

End-to-end example
------------------

1. Define problem
~~~~~~~~~~~~~~~~~~

We want to compute the expectation value of a quantum state (circuit) with respect to a certain operator.
Here we are using the H2 molecule and an arbitrary circuit as the quantum state:

.. code-block:: python


    from qiskit import QuantumCircuit
    from qiskit.quantum_info import SparsePauliOp

    # Step 1: Define operator
    op = SparsePauliOp.from_list(
        [
            ("II", -1.052373245772859),
            ("IZ", 0.39793742484318045),
            ("ZI", -0.39793742484318045),
            ("ZZ", -0.01128010425623538),
            ("XX", 0.18093119978423156),
        ]
    )

    # Step 2: Define quantum state
    state = QuantumCircuit(2)
    state.x(0)
    state.x(1)

.. _a-legacy-opflow:

1.a. [Legacy] Convert problem to ``opflow``
###########################################

|qiskit.opflow|_ provided its own classes to represent both
operators and quantum states, so the problem defined above would be wrapped as:

.. code-block:: python

    from qiskit.opflow import CircuitStateFn, PauliSumOp

    opflow_op = PauliSumOp(op)
    opflow_state = CircuitStateFn(state)

This step is no longer necessary using the primitives.

.. note::

    For more information on migrating from |qiskit.opflow|_, see the `opflow migration guide <qisk.it/opflow_migration>`_ .

2. Calculate expectation values on real device or cloud simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

2.a. [Legacy] Using ``opflow`` + ``backend.run()``
####################################################

You can see the number of steps that legacy workflow involved to be able to compute an expectation
value:

.. note::

    You can replace ``ibmq_qasm_simulator`` with your device name to see the
    complete workflow for a real device.

.. code-block:: python

    from qiskit.opflow import StateFn, PauliExpectation, CircuitSampler
    from qiskit_ibm_provider import IBMProvider

    # Define the state to sample
    measurable_expression = StateFn(opflow_op, is_measurement=True).compose(opflow_state)

    # Convert to expectation value calculation object
    expectation = PauliExpectation().convert(measurable_expression)

    # Define provider and backend (formerly imported from IBMQ)
    provider = IBMProvider()
    backend = provider.get_backend("ibmq_qasm_simulator")

    # Inject backend into circuit sampler
    sampler = CircuitSampler(backend).convert(expectation)

    # Evaluate
    expectation_value = sampler.eval().real

.. code-block:: python

    >>> print("expectation: ", expectation_value)
    expectation:  -1.065734058826613

2.b. [New] Using Runtime ``Estimator``
###########################################

Now, you can notice how the ``Estimator`` simplifies the user-side syntax, which makes it a more
convenient tool for algorithm design.

.. note::

    You can replace ``ibmq_qasm_simulator`` with your device name to see the
    complete workflow for a real device.

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService, Estimator

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")

    estimator = Estimator(session=backend)

    expectation_value = estimator.run(state, op).result().values

Note that the Estimator returns a list of values, as it can performed batched evaluations.

.. code-block:: python

    >>> print("expectation: ", expectation_value)
    expectation:  [-1.06329149]

The Runtime ``Estimator`` offers a series of features and tuning options that do not have a legacy alternative
"to migrate from",
but can help improve your performance and results. For more information, you can visit:

- `The tutorial on error mitigation in the Runtime Primitives <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/tutorials/Error-Suppression-and-Error-Mitigation.html>`_
- `The how-to setting execution options in the Runtime Primitives <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/options.html>`_
- `The API reference for execution options in the Runtime Primitives <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.options.Options.html#qiskit_ibm_runtime.options.Options>`_
- `The how-to on sessions for faster execution of iterative workloads <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/run_session.html>`_


3. Other execution alternatives (non-Runtime)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some cases, you might want to test your algorithm using local simulation. For this means, we
will show you two more migration paths using non-runtime primitives. Let's say that you want to
solve the problem defined above with a local statevector simulation.

3.a. [Legacy] Using Qiskit Aer's Simulator
###########################################

.. code-block:: python

    from qiskit.opflow import StateFn, PauliExpectation, CircuitSampler
    from qiskit_aer import AerSimulator

    # Define the state to sample
    measurable_expression = StateFn(opflow_op, is_measurement=True).compose(opflow_state)

    # Convert to expectation value calculation object
    expectation = PauliExpectation().convert(measurable_expression)

    # Define statevector simulator
    simulator = AerSimulator(method="statevector", shots=100)

    # Inject backend into circuit sampler
    sampler = CircuitSampler(simulator).convert(expectation)

    # Evaluate
    expectation_value = sampler.eval().real

.. code-block:: python

    >>> print("expectation: ", expectation_value)
    expectation:  -1.0636533500290943


3.b. [New] Using Reference ``Estimator`` or Aer ``Estimator``
##############################################################

The Reference ``Estimator`` allows to perform either an exact or a shot-based noisy simulation based
on the ``Statevector`` class in the ``qiskit.quantum_info`` module.

.. code-block:: python

    from qiskit.primitives import Estimator

    estimator = Estimator()

    result = estimator.run(state, op).result().values

    # for shot-based simulation:
    expectation_value = estimator.run(state, op, shots=100).result().values

.. code-block:: python

    >>> print("expectation: ", expectation_value)
    expectation:  [-1.03134297]

You can still access the Aer Simulator through its dedicated
``Estimator``. This can come in handy for performing simulations with noise models. In this example,
the simulation method has been fixed to match the result from 3.a.

.. code-block:: python

    from qiskit_aer.primitives import Estimator # all that changes is the import!!!

    estimator = Estimator(run_options= {"method": "statevector"})

    result = estimator.run(state, op).result().values

    # for shot-based simulation:
    expectation_value = estimator.run(state, op, shots=100).result().values

.. code-block:: python

    >>> print("expectation: ", expectation_value)
    expectation:  [-1.06365335]

For more information on using the Aer Primitives, you can check out this
`VQE tutorial <https://qiskit.org/documentation/tutorials/algorithms/03_vqe_simulation_with_noise.html>`_ .

For more information on running noisy simulations with the **Runtime Pritives**, you can see this
`how-to <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/noisy_simulators.html>`_.