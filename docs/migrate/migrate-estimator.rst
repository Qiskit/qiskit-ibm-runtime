Calculate expectation values in an algorithm
==============================================

The role of the `Estimator` primitive is two-fold: on one hand, it acts as an entry point to the quantum devices or simulators, replacing `backend.run()` (or `QuantumInstance.execute()`). On the other hand, it is an **algorithmic abstraction** for expectation value calculations, which removes the need to perform operations to construct the final expectation circuit. This results in a considerable reduction of the code complexity, and a more compact algorithm design. 

The following example uses common tools from the ``qiskit.opflow`` module as a reference for the "legacy way of doing things", but we acknowledge that some of you might have used custom code for this task. In that case, you can decide between keeping your custom code and replacing `backend.run()` with a `Sampler`, or replacing your custom code with the `Estimator` primitive.


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

.. _legacy-opflow:

Legacy methods (using opflow)
-----------------------------

Compare this section to :ref:`new-primitives`.

`Opflow <https://qiskit.org/documentation/apidoc/opflow.html>`__ provided its own classes to represent both operators and quantum states:

.. code-block:: python

    from qiskit.opflow import CircuitStateFn, PauliSumOp

    opflow_op = PauliSumOp(op)
    opflow_state = CircuitStateFn(state) # convert to a state

.. _legacy-exact:

Option 1: Calculate the expectation value exactly (classical)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare this section to :ref:`new-exact`.

Sometimes the system is small enough that we can compute the expectation value classically. With opflow, this was done by composing the circuit and operator states, then calling for the exact evaluation method:


.. code-block:: python

    opflow_state_func = opflow_state.adjoint().compose(opflow_op).compose(opflow_state)
    expectation_value_1 = opflow_state_func.eval().real # easy expectation value, use for small systems only!

    print("exact: ", expectation_value_1)

.. _legacy-construct:

Option 2: Construct the expectation circuit and sample on a system or simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare this section to :ref:`new-construct`.

.. code-block:: python

    from qiskit.opflow import StateFn, PauliExpectation, CircuitSampler

    # Define the state to sample
    measurable_expression = StateFn(opflow_op, is_measurement=True).compose(opflow_state)

    # Convert to expectation value calculation object
    expectation = PauliExpectation().convert(measurable_expression)

    # Note that there are other expectation value methods: MatrixExpectation(), AerPauliExpectation(), 
    # but they are used just like PauliExpectation()

Next, the actual calculation is done by the `CircuitSampler` class, which receives a backend or `QuantumInstance` and the expectation object. Here are some examples of how it can be used:

.. _legacy-run-aer:

1. Run locally by using an AerSimulator
*****************************************

Compare this section to :ref:`new-run-aer`.

.. code-block:: python

   from qiskit.providers.aer import AerSimulator

    # define backend -> local simulator
    simulator = AerSimulator() 

    # inject backend into circuit sampler
    sampler = CircuitSampler(simulator).convert(expectation)

    # evaluate
    expectation_value_2 = sampler.eval().real

    print("sampled: ", expectation_value_2)

.. _legacy-run-remote:

2. Run on a remote simulator or real backend
*********************************************

Compare this section to :ref:`new-run-remote`.

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


.. _new-primitives:

New method: Use primitives
-----------------------------

Compare this section to :ref:`legacy-opflow`.


.. _new-exact:

Option 1: Calculate the expectation value exactly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare this section to :ref:`legacy-exact`.

This can be done with the Estimator primitive in `qiskit.primitives`:


.. code-block:: python

    from qiskit.primitives import Estimator

    estimator = Estimator()

    result = estimator.run([state], [op]).result().values
    print(result)

.. _new-construct:

Option 2: Construct the expectation circuit and sample on a system or simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare this section to :ref:`legacy-construct`.

.. _new-construct-run-terra:

0. Run locally by using the terra primitive
*********************************************

The reference ``Estimator`` in ``qiskit.primitives`` uses the ``qiskit.quantum_info.Statevector`` class to compute expectation values. If the number of shots is specificed, the result will no longer be exact.

.. code-block:: python

   from qiskit.primitives import Estimator

    estimator = Estimator(options={"shots": 1024})

    result = estimator.run([state], [op]).result().values
    print(result)

.. _new-run-aer:

1. Run locally by using an AerSimulator 
*********************************************

Compare this section to :ref:`legacy-run-aer`.

.. code-block:: python

    from qiskit_aer.primitives import Estimator

    estimator = Estimator(run_options={"shots": 1024})

    result = estimator.run([state], [op]).result().values
    print(result)

.. _new-run-remote:

2. Run on a remote simulator or real backend
*********************************************

Compare this section to :ref:`legacy-run-remote`.

.. code-block:: python
    
    from qiskit_ibm_runtime import QiskitRuntimeService, Estimator

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")

    estimator = Estimator(session=backend)

    result = estimator.run(state, op).result().values
    print(result)
