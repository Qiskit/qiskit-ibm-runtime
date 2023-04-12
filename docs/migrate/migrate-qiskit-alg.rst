Work with updated Qiskit algorithms
===================================
.. |QuantumInstance| replace:: ``QuantumInstance``
.. _QuantumInstance: https://qiskit.org/documentation/stubs/qiskit.utils.QuantumInstance.html

.. |qiskit.algorithms| replace:: ``qiskit.algorithms``
.. _qiskit.algorithms: https://qiskit.org/documentation/apidoc/algorithms.html

.. |qiskit.opflow| replace:: ``qiskit.opflow``
.. _qiskit.opflow: https://qiskit.org/documentation/apidoc/opflow.html

.. |qiskit.quantum_info| replace:: ``qiskit.quantum_info``
.. _qiskit.quantum_info: https://qiskit.org/documentation/apidoc/quantum_info.html

The |qiskit.algorithms|_ module has been updated to leverage the primitives in all of its classes.
In practice, this means that:

1. All algorithms now take in a primitive instead of a ``Backend`` or |QuantumInstance|_
2. Some algorithms now have a new import path
3. New primitive-specific algorithms have been introduced
4. As a side effect of the primitives refactoring, |qiskit.algorithms|_ no longer
   use |qiskit.opflow|_ 

.. raw:: html

    <br>

Using **Runtime Sessions** can be particularly advantageous when working with variational algorithms, as they
present iterative workloads that can submit multiple jobs per iteration. On top of this, the runtime
primitives allow to try out different error mitigation techniques with no changes to the algorithm,
just a simple option configuration.

.. note::

	The following end-to-end example illustrates how to use one of the refactored algorithms from 		
	|qiskit.algorithms|_ with the **Qiskit Runtime primitives**. For a detailed explanation of other algorithm
	migration scenarios, see the `Qiskit algorithms migration guide <https://qisk.it/algo_migration>`_.

Example: VQE
-------------

The legacy ``VQE`` algorithm has been split into two new implementations:

- ``VQE`` : Based on the Estimator
- ``SamplingVQE`` : For diagonal operators, based on the Sampler

The choice of implementation depends on the use case — whether you are interested in accessing the
probability distribution corresponding to a quantum state (``SamplingVQE``) or an estimation of
the ground state energy which might require, for example, measurements in multiple bases (``VQE``).

Let's see the workflow changes for the Estimator-based VQE implementation:

Step 1: Problem definition
~~~~~~~~~~~~~~~~~~~~~~~~~~

The problem definition step is common to the old and new workflow: defining the Hamiltonian, ansatz,
optimizer and initial point.

The only difference is that the operator definition now relies on |qiskit.quantum_info|_ instead
of |qiskit.opflow|_ . In practice, this means that all ``PauliSumOp`` dependencies should be replaced
by ``SparsePauliOp``. 

.. 
    Add this back in when it's done and we have the link. 
    For more information, you can refer to the `Opflow migration guide <http://qisk.it/opflow_migration>`_.

.. note::

   All of the refactored classes in |qiskit.algorithms|_ now take in operators as instances of
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

.. raw:: html

    <details>
    <summary><a>Legacy VQE</a></summary>

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
.. raw:: html

    </details>

.. raw:: html

    <details>
    <summary><a>New VQE</a></summary>

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
.. raw:: html

    </details>


Step 2: Backend setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. _session: https://quantum-computing.ibm.com/lab/docs/iql/manage/systems/sessions

Let's say that you want to run VQE on the ``ibmq_qasm_simulator`` in the cloud. Before you would load you IBMQ account,
get the corresponding backend from the provider, and use it to set up a |QuantumInstance|_. Now, you need to initialize
a ``QiskitRuntimeService``, open a `session`_ and use it to instantiate your :class:`.Estimator`.

.. raw:: html

    <details>
    <summary><a>Legacy VQE</a></summary>

.. code-block:: python

    from qiskit.utils import QuantumInstance
    from qiskit import IBMQ

    IBMQ.load_account()
    provider = IBMQ.get_provider(hub='MY_HUB')
    my_backend = provider.get_backend("ibmq_qasm_simulator")
    qi = QuantumInstance(backend=my_backend)

.. raw:: html

    </details>

.. raw:: html

    <details>
    <summary><a>New VQE</a></summary>

.. code-block:: python

    from qiskit_ibm_runtime import Estimator, QiskitRuntimeService, Session

    # no more IBMQ import or .load_account()
    service = QiskitRuntimeService(channel="ibm_quantum")
    session = Session(service, backend="ibmq_qasm_simulator") # open session
    estimator = Estimator(session = session)

.. raw:: html

    </details>

Step 3: Run VQE
~~~~~~~~~~~~~~~

Now that both the problem and the execution path have been set up, you can instantiate and run VQE. Close the session only if all jobs are finished and you don't need to run more jobs in the session.

.. attention::

    ``VQE`` is one of the algorithms with a changed import path. If you do not specify the full path during the import,
    you might run into conflicts with the legacy code.

.. raw:: html

    <details>
    <summary><a>Legacy VQE</a></summary>

.. code-block:: python

    from qiskit.algorithms.minimum_eigen_solvers import VQE

    vqe = VQE(ansatz, optimizer, quantum_instance=qi)
    result = vqe.compute_minimum_eigenvalue(hamiltonian)

.. raw:: html

    </details>

.. raw:: html

    <details>
    <summary><a>New VQE</a></summary>

.. code-block:: python

    # note change of namespace
    from qiskit.algorithms.minimum_eigensolvers import VQE

    vqe = VQE(estimator, ansatz, optimizer)
    result = vqe.compute_minimum_eigenvalue(hamiltonian)

    # close session!
    session.close()

.. raw:: html

    </details>

Using context managers
~~~~~~~~~~~~~~~~~~~~~~~

We recommend that you initialize your primitive and run your algorithm using
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
* See the `Session documentation <./how_to/run_session.html>` for further information about the Qiskit Runtime sessions.
* See the `How to run a primitive in a session <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/how_to/run_session.html>`__ topic for detailed code examples.
* See the `Qiskit algorithm documentation <https://qiskit.org/documentation/apidoc/algorithms.html>`__ for details about each algorithm.
* See the `Qiskit algorithm tutorials <https://qiskit.org/documentation/tutorials/algorithms/index.html>`__ for examples of how to use algorithms.
* Read the blog `Introducing Qiskit Algorithms With Qiskit Primitives! <https://medium.com/qiskit/introducing-qiskit-algorithms-with-qiskit-runtime-primitives-d89703ecfca3>`__ for an introduction to using the updated algorithms.


