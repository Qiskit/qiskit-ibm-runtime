Work with updated Qiskit algorithms
===================================

The ``qiskit.algorithms`` module has been updated to leverage the primitives in all of it classes.
In practice, this means that:

1. All algorithms now take in a primitive instead of a ``Backend`` or ``QuantumInstance``
2. Some algorithms now have a new import path
3. New primitive-specific algorithms have been introduced
4. As a side effect of the primitives refactoring, the ``qiskit.algorithms`` no longer
   use ``opflow`` under the hood

.. raw:: html

    <br>

Using runtime sessions can be particularly advantageous when working with variational algorithms, as they
present iterative workloads that can submit multiple jobs per iteration. On top of this, the runtime
primitives allow to try out different error mitigation techniques with no changes to the algorithm,
just a simple option configuration.

The migration of ``qiskit.algorithms`` to work with primitives (any primitive implementation) has been explained
in detail in the algorithm migration guide. However, we will now show an example to point out how to adapt
these primitive-generic guidelines to the specific case of the Runtime Primitives.

Example: VQE
-------------

The legacy ``VQE`` algorithm has been split into two new implementations:

- ``VQE`` : based on the Estimator
- ``SamplingVQE`` : for diagonal operators, based on the Sampler

The choice of implementation depends on the use case — whether you are interested in accessing the
probability distribution corresponding to a quantum state (``SamplingVQE``) or an estimation of
the ground state energy which might require, for example, measurements in multiple bases (``VQE``).

Let's see the workflow changes for the Estimator-based VQE implementation:

Step 1: Problem Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~

The problem definition step is common to the old and new workflow: defining the hamiltonian, ansatz,
optimizer and initial point.

The only difference is that the operator definition now relies on ``quantum_info`` instead
of ``opflow``. In practice, this means that all ``PauliSumOp`` dependencies should be replaced
by ``SparsePauliOp``.

.. note::

   All of the refactored classes in ``qiskit.algorithms`` now take in operators as instances of
   ``SparsePauliOp`` instead of ``PauliSumOp``.

The ansatz, optimizer and initial point are defined identically:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: python

    from qiskit.algorithms.optimizers import SLSQP
    from qiskit.circuit.library import TwoLocal

    # define ansatz and optimizer
    num_qubits = 2
    ansatz = TwoLocal(num_qubits, "ry", "cz")
    optimizer = SLSQP(maxiter=100)

    # define initial point
    init_pt = [-0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1]

    # hamiltonian/operator --> use SparsePauliOp or Operator
    from qiskit.quantum_info import SparsePauliOp

    hamiltonian = SparsePauliOp.from_list(
        [
            ("II", -1.052373245772859),
            ("IZ", 0.39793742484318045),
            ("ZI", -0.39793742484318045),
            ("ZZ", -0.01128010425623538),
            ("XX", 0.18093119978423156),
        ]
    )

The operator definition changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Legacy VQE**

.. code-block:: python

    from qiskit.opflow import PauliSumOp

    hamiltonian = PauliSumOp.from_list(
        [
            ("II", -1.052373245772859),
            ("IZ", 0.39793742484318045),
            ("ZI", -0.39793742484318045),
            ("ZZ", -0.01128010425623538),
            ("XX", 0.18093119978423156),
        ]
    )


**New VQE**

.. code-block:: python

    from qiskit.quantum_info import SparsePauliOp

    hamiltonian = SparsePauliOp.from_list(
        [
            ("II", -1.052373245772859),
            ("IZ", 0.39793742484318045),
            ("ZI", -0.39793742484318045),
            ("ZZ", -0.01128010425623538),
            ("XX", 0.18093119978423156),
        ]
    )



Step 2: Backend setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say that you want to run VQE on the ``ibmq_qasm_simulator`` in the cloud. Before you would load you IBMQ account,
get the corresponding backend from the provider, and use it to set up a ``QuantumInstance``. Now, you need to initialize
a ``QiskitRuntimeService``, open a session and use it to instantiate your ``Estimator``.

**Legacy VQE**

.. code-block:: python

    from qiskit.utils import QuantumInstance
    from qiskit import IBMQ

    IBMQ.load_account()
    provider = IBMQ.get_provider(hub='MY_HUB')
    my_backend = provider.get_backend("ibmq_qasm_simulator")
    qi = QuantumInstance(backend=my_backend)


**New VQE**

.. code-block:: python

    from qiskit_ibm_runtime import Estimator, QiskitRuntimeService, Session

    # no more IBMQ import or .load_account()
    service = QiskitRuntimeService(channel="ibm_quantum")
    session = Session(service, backend="ibmq_qasm_simulator") # open session
    estimator = Estimator(session = session)


Step 3: Run VQE
~~~~~~~~~~~~~~~

Now that you have set up both the problem and the execution path, you can instantiate and run VQE. Please note
that after running your program, you must **close your session**.

.. attention::

    ``VQE`` is one of the algorithms with a changed import path. If you do not specify the full path during the import,
    you might run into conflicts with the legacy code.

**Legacy VQE**

.. code-block:: python

    from qiskit.algorithms.minimum_eigen_solvers import VQE

    vqe = VQE(ansatz, optimizer, quantum_instance=qi)
    result = vqe.compute_minimum_eigenvalue(hamiltonian)

**New VQE**

.. code-block:: python

    # note change of namespace
    from qiskit.algorithms.minimum_eigensolvers import VQE

    vqe = VQE(estimator, ansatz, optimizer)
    result = vqe.compute_minimum_eigenvalue(hamiltonian)

    # close session!
    session.close()


Using Context Managers
~~~~~~~~~~~~~~~~~~~~~~~

To not forget about closing sessions, we recommend that you initialize your primitive and run your algorithm using
a context manager. The code for steps 2 and 3 would then look like:

.. code-block:: python

    from qiskit_ibm_runtime import Estimator, QiskitRuntimeService, Session
    from qiskit.algorithms.minimum_eigensolvers import VQE

    service = QiskitRuntimeService(channel="ibm_quantum")

    with Session(service, backend="ibmq_qasm_simulator") as session:

        estimator = Estimator() # no need to pass the session explicitly
        vqe = VQE(estimator, ansatz, optimizer, gradient=gradient, initial_point=init_pt)
        result = vqe.compute_minimum_eigenvalue(hamiltonian)


Related links
----------------

* See the `Qiskit algorithm documentation <https://qiskit.org/documentation/apidoc/algorithms.html>`__ for details about each algorithm.
* See the `Qiskit algorithm tutorials <https://qiskit.org/documentation/tutorials/algorithms/index.html>`__ for examples of how to use algorithms.
* Read the blog`Introducing Qiskit Algorithms With Qiskit Primitives! <https://medium.com/qiskit/introducing-qiskit-algorithms-with-qiskit-runtime-primitives-d89703ecfca3>`__ for an introduction to using the updated algorithms.


