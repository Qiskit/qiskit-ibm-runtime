Calculate expectation values in an algorithm
==============================================

The Estimator primitive serves a double purpose here:

* Acts as entry point to quantum systems and simulators by replacing `backend.run()`  (in the case of the `qiskit-ibm-runtime.Estimator`), as well as the tools we had for exact computations (local) that we can now replace with the `qiskit.primitives.Estimator`.
* Acts as an **algorithmic abstraction**. Recall that to be executable in a real device, the expectation value calculation must represented as a single quantum circuit. This can be done by a series of operations that were previously left to the user. Most users relied on a series of Qiskit Terra tools  (in `qiskit.opflow`) to perform these operations, so this method will be shown in the legacy implementation section.  

  The new method is much shorter and most of the tools from `qiskit.opflow` used in these examples have been rendered obsolete by the primitives. 


Problem definition 
-------------------------------

We want to compute the expectation value of a quantum state (circuit) with respect to a certain operator. Here we are using the H2 molecule and an arbitrary circuit as the quantum state:


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

Legacy methods (using opflow)
-----------------------------

Opflow provided its own classes to represent both operators and quantum states:

.. code-block:: python

    from qiskit.opflow import CircuitStateFn, PauliSumOp

    opflow_op = PauliSumOp(op)
    opflow_state = CircuitStateFn(state) # convert to a state

Option 1: Calculate the expectation value exactly (classical)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes the system is small enough that we can compute the expectation value classically. With opflow, this was done by composing the circuit and operator states, then calling for the exact evaluation method:


.. code-block:: python

    opflow_state_func = opflow_state.adjoint().compose(opflow_op).compose(opflow_state)
    expectation_value_1 = opflow_state_func.eval().real # easy expectation value, use for small systems only!

    print("exact: ", expectation_value_1)

Option 2: Construct the expectation circuit and sample on a system or simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from qiskit.opflow import StateFn, PauliExpectation, CircuitSampler

    # Define the state to sample
    measurable_expression = StateFn(opflow_op, is_measurement=True).compose(opflow_state)

    # Convert to expectation value calculation object
    expectation = PauliExpectation().convert(measurable_expression)

    # Note that there are other expectation value methods: MatrixExpectation(), AerPauliExpectation(), 
    # but they are used just like PauliExpectation()

Next, the actual calculation is done by the `CircuitSampler` class, which receives a backend or `QuantumInstance` and the expectation object. Here are some examples of how it can be used:

1. Run locally by using an AerSimulator
*****************************************

.. code-block:: python

   from qiskit.providers.aer import AerSimulator

    # define backend -> local simulator
    simulator = AerSimulator() 

    # inject backend into circuit sampler
    sampler = CircuitSampler(simulator).convert(expectation)

    # evaluate
    expectation_value_2 = sampler.eval().real

    print("sampled: ", expectation_value_2)

2. Run on a remote simulator or real backend
*********************************************

Here we use the `ibmq_qasm_simulator`, but the workflow is the same when using a real device.

.. code-block:: python

    from qiskit import IBMQ

    IBMQ.load_account()
    provider = IBMQ.get_provider(hub='ibm-q')
    backend = provider.get_backend("ibmq_qasm_simulator")

    # inject backend into circuit sampler
    sampler = CircuitSampler(backend).convert(expectation) 

    # evaluate
    expectation_value_4 = sampler.eval().real

    print("sampled: ", expectation_value_4)


New method: Use primitives
-----------------------------

Opflow provided its own classes to represent both operators and quantum states:

.. code-block:: python

    from qiskit.opflow import CircuitStateFn, PauliSumOp

    opflow_op = PauliSumOp(op)
    opflow_state = CircuitStateFn(state) # convert to a state

Option 1: Calculate the expectation value exactly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This can be done with the Estimator primitive in `qiskit.primitives`:


.. code-block:: python

    from qiskit.primitives import Estimator

    estimator = Estimator()

    result = estimator.run([state], [op]).result().values
    print(result)

Option 2: Construct the expectation circuit and sample on a system or simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

0. Run locally by using the terra primitive
*********************************************

For the terra primitive, if no shots are specified, it performs an exact calculation. If shots are specified, it performs a shot-based simulation (not quite qasm, as you can see). There is no real legacy alternative for this:

.. code-block:: python

   from qiskit.primitives import Estimator

    estimator = Estimator(options={"shots": 1024})

    result = estimator.run([state], [op]).result().values
    print(result)

1. Run locally by using an AerSimulator 
*********************************************

.. code-block:: python

    from qiskit_aer.primitives import Estimator

    estimator = Estimator(run_options={"shots": 1024})

    result = estimator.run([state], [op]).result().values
    print(result)

2. Run on a remote simulator or real backend
*********************************************

.. code-block:: python
    
    from qiskit_ibm_runtime import QiskitRuntimeService, Estimator

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")

    estimator = Estimator(session=backend)

    result = estimator.run([state], [op]).result().values
    print(result)
