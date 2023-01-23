Work with updated Qiskit algorithms
===================================

All Qiskit algorithms now use primitives to evaluate expectation values or sample circuits.  Therefore, when you're calling an algorithm, you need to pass it a primitive instead of a backend. 

Recall that with backend.run, one can initialize any subclass of the base class and pass it to the backend parameter. This can, for example, be a backend you initialize from ibmq-provider, or Qiskit Aer (simulator), or even a third party.

With the primitives, one can similarly initialize any subclass of the base primitive classes (BaseEstimator and BaseSampler). For example, this can be ibm-runtime primitive or Qiskit Aer primitive.

Overview
--------

To migrate code that uses Qiskit algorithms, such as VQE, you need to do the following:
* Initialize your account, specifying the backend that you want to use.
* Reviw the algorithm's attributes in the `Qiskit documentation (https://qiskit.org/documentation/index.html)`__ to determine which primitive the algorithm now uses. 
* Change the attributes in the algorithm call to refer to that primitive instead of the backend, and add or remove other attributes as necessary.
* Add and remove attribute definitions as necessary.
* Import the appropriate libraries.  These will probably be `Estimator`, `Sampler`, `QiskitRuntimeService`, or some combination of those. 


Note that for our example (VQE), there are actually two algorithms now.  VQE has been updated to use Estimator instead of a quantum instance. SamplingVQE is the new VQE algorithm that uses the Sampler primitive and is optimized for diagonal Hamiltonians. 

Calling the VQE algorithm that doesn't use primitives (deprecated)
--------------------------------------------------------------------

.. code-block:: python

    from qiskit import BasicAer 
    from qiskit.algorithms.minimum_eigen_solvers import VQE 
    from qiskit.algorithms.optimizers import SLSQP 
    from qiskit.circuit.library import TwoLocal 
    from qiskit.opflow import PauliSumOp 
    from qiskit.quantum_info import SparsePauliOp 
 
 
    hamiltonian = PauliSumOp(SparsePauliOp.from_list([(“II”, -1), (“IZ”, 0.3), (“XI”, -0.3), (“ZY”, -0.01), (“YX”, 0.1)])) 
 
    quantum_instance = BasicAer.get_backend(“statevector_simulator”) 
    optimizer = SLSQP() 
    ansatz = TwoLocal(rotation_blocks=[“ry”, “rz”], entanglement_blocks=”cz”) 
 
    vqe = VQE(ansatz, optimizer, quantum_instance=quantum_instance) 
    result = vqe.compute_minimum_eigenvalue(operator=hamiltonian) 
    eigenvalue = result.eigenvalue



Calling the VQE algorithm that uses Estimator
--------------------------------------------------

.. code-block:: python

    from qiskit.algorithms.minimum_eigensolvers import VQE 
    from qiskit.algorithms.optimizers import SLSQP 
    from qiskit.circuit.library import TwoLocal 
    from qiskit.quantum_info import SparsePauliOp 
    from qiskit.primitives import Estimator 
    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")
 
 
    hamiltonian = SparsePauliOp.from_list([(“II”, -1), (“IZ”, 0.3), (“XI”, -0.3), (“ZY”, -0.01), (“YX”, 0.1)]) 
 
    estimator = Estimator() 
    optimizer = SLSQP() 
    ansatz = TwoLocal(rotation_blocks=[“ry”, “rz”], entanglement_blocks=”cz”) 
 
    vqe = VQE(estimator, ansatz, optimizer) 
    result = vqe.compute_minimum_eigenvalue(operator=hamiltonian) 
    eigenvalue = result.eigenvalue


Calling the VQE algorithm that uses Sampler (SamplingVQE)
---------------------------------------------------------

.. code-block:: python

    from qiskit.algorithms.minimum_eigensolvers import SamplingVQE 
    from qiskit.algorithms.optimizers import SLSQP 
    from qiskit.circuit.library import TwoLocal 
    from qiskit.primitives import Sampler 
    from qiskit.quantum_info import SparsePauliOp 
    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend("ibmq_qasm_simulator")
 
 
    operator = SparsePauliOp.from_list([(“ZZ”, 1), (“IZ”, -0.5), (“II”, 0.12)]) 
 
    sampler = Sampler() 
    ansatz = TwoLocal(rotation_blocks=[“ry”, “rz”], entanglement_blocks=”cz”) 
    optimizer = SLSQP() 
 
    sampling_vqe = SamplingVQE(sampler, ansatz, optimizer) 
    result = sampling_vqe.compute_minimum_eigenvalue(operator) 
    eigenvalue = result.eigenvalue


Related links
-------------

* `VQE implementation with Estimator code <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/minimum_eigensolvers/vqe.py>`__
* `VQE implementation with Estimator documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.minimum_eigensolvers.VQE.html#qiskit.algorithms.minimum_eigensolvers.VQE>`__
* `VQE implementation with Estimator code <https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/algorithms/minimum_eigensolvers/sampling_vqe.py>`__
* `VQE implementation with Estimator documentation <https://qiskit.org/documentation/stubs/qiskit.algorithms.minimum_eigensolvers.SamplingVQE.html#qiskit.algorithms.minimum_eigensolvers.SamplingVQE>`__
* `Primitives overview and usage <https://qiskit.org/documentation/apidoc/primitives.html>`__