Work with updated Qiskit algorithms
===================================

The Qiskit algorithms have been updated to use the primitives.  We will show the changes to the VQE algorithm, but you should review any algorithm you use to understand how it has changed. 

Example:  Changes to VQE
----------------------------

The VQE algorithm has changed more than most, in that there are now two versions of VQE: `SamplingVQE`, which uses the sampler primitive and is optimized for diagonal Hamiltonians, and `VQE`, which uses the estimator primitive. The choice of the algorithm depends on the use case — whether you are interested in accessing the probability distribution corresponding to a quantum state or an estimation of the ground state energy which might require, for example, measurements in multiple bases.

The updated VQE algorithm now uses the Estimator instead of a quantum instance, and the SparsePauliOp instead of the PauliSumOp (although the PauliSumOp is currently still supported). The comparison of the current and the old version of VQE on a simple example follows:

.. list-table:: VQE usage changes
   :widths: 50 50
   :header-rows: 1

   * - QuantumInstance VQE
     - Estimator VQE
   * - .. code-block:: python
   
            from qiskit.algorithms.minimum_eigen_solvers import VQE
            from qiskit.utils import QuantumInstance
            from qiskit import Aer

            qi = QuantumInstance(
                backend=Aer.get_backend('statevector_simulator'))
   
            vqe = VQE(ansatz, optimizer, quantum_instance=qi)
            result = vqe.compute_minimum_eigenvalue(hamiltonian)
     - .. code-block:: python

            # note change of namespace
            from qiskit.algorithms.minimum_eigensolvers import VQE
            from qiskit.primitives import Estimator

            estimator = Estimator()
    
            vqe = VQE(estimator, ansatz, optimizer)
            result = vqe.compute_minimum_eigenvalue(hamiltonian)

Related links
----------------

See the `Qiskit algorithm documentation <https://qiskit.org/documentation/apidoc/algorithms.html>`__ for details about each algorithm.
See the `Qiskit algorithm tutorials <https://qiskit.org/documentation/tutorials/algorithms/index.html>`__ for examples of how to use algorithms.
Read the blog`Introducing Qiskit Algorithms With Qiskit Primitives! <https://medium.com/qiskit/introducing-qiskit-algorithms-with-qiskit-runtime-primitives-d89703ecfca3>`__ for an introduction to using the updated algorithms.

