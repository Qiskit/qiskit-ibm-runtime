Configure error suppression
=============================

Error suppression techniques optimize and transform your circuit at the point of compilation to minimize errors. This is the most basic error handling technique.  

Error suppression typically results in some classical pre-processing overhead to your overall runtime. Therefore, it is important to achieve a balance between perfecting your results and ensuring that your job completes in a reasonable amount of time. 

Primitives let you employ error suppression techniques by setting the optimization level (``optimization_level`` option) and by choosing advanced transpilation options. 

Setting the optimization level
------------------------------

The optimization_levels setting specifies how much optimization to perform on the circuits. Higher levels generate more optimized circuits, at the expense of longer transpilation times.

+--------------------+---------------------------------------------------------------------------------------------------+
| Optimization Level | Estimator & Sampler                                                                               |
+====================+===================================================================================================+
| 0                  | No optimization: typically used for hardware characterization                                     |
|                    |                                                                                                   |
|                    | - basic translation                                                                               |
|                    | - layout (as specified)                                                                           |
|                    | - routing (stochastic swaps)                                                                      |
|                    |                                                                                                   |
+--------------------+---------------------------------------------------------------------------------------------------+
| 1                  | Light optimization:                                                                               |
|                    |                                                                                                   |
|                    | - Layout (trivial → vf2 → SabreLayout if routing is required)                                     |
|                    | - routing (SabreSWAPs if needed)                                                                  |
|                    | - 1Q gate optimization                                                                            |
|                    | - Error Suppression: Dynamical Decoupling                                                         |
|                    |                                                                                                   |
+--------------------+---------------------------------------------------------------------------------------------------+
| 2                  | Medium optimization:                                                                              |
|                    |                                                                                                   |
|                    | - Layout/Routing: Optimization level 1 (without trivial) + heuristic optimized with greater       |
|                    |      search depth and trials of optimization function                                             |
|                    | - commutative cancellation                                                                        |
|                    | - Error Suppression: Dynamical Decoupling                                                         |
|                    |                                                                                                   |
+--------------------+---------------------------------------------------------------------------------------------------+
| 3 (default)        | High Optimization:                                                                                |
|                    |                                                                                                   |
|                    | * Optimization level 2 + heuristic optimized on layout/routing further with greater effort/trials |
|                    | * 2 qubit KAK optimization                                                                        |
|                    | * Error Suppression: Dynamical Decoupling                                                         |
|                    |                                                                                                   |
+--------------------+---------------------------------------------------------------------------------------------------+

Example: configure Estimator with optimization levels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService, Session, Estimator, Options
    from qiskit.circuit.library import RealAmplitudes
    from qiskit.quantum_info import SparsePauliOp

    service = QiskitRuntimeService()
    options = Options(optimization_level=2)

    psi = RealAmplitudes(num_qubits=2, reps=2)
    H = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
    theta = [0, 1, 1, 2, 3, 5]

    with Session(service=service, backend="ibmq_qasm_simulator") as session:
        estimator = Estimator(session=session, options=options)
        job = estimator.run(circuits=[psi], observables=[H], parameter_values=[theta])
        psi1_H1 = job.result()

.. note:: 
    If optimization level is not specified, the service uses ``optimization_level = 3``.  

Example: configure Sampler with optimization levels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Options

    service = QiskitRuntimeService()
    options = Options(optimization_level=3)

    with Session(service=service, backend="ibmq_qasm_simulator") as session:
        sampler = Sampler(session=session, options=options)
  
Advanced transpilation options
------------------------------

You also have the ability to tune a variety of advanced options to configure your transpilation strategy further. These methods can be used alongside optimization levels.  They allow you to change the options of interest and let your optimization level manage the rest.  

Most of the transpilation options are inherited from `qiskit.compiler.transpile <https://qiskit.org/documentation/stubs/qiskit.compiler.transpile.html>`__. 

+---------------------------------------------------------------+-------------------------------------------------------------------------+
| Options                                                       | Description                                                             |
+===============================================================+=========================================================================+
| options.transpilation.initial_layout(Union[dict, List, None]) | Initial position of virtual qubits on physical qubits.                  |
+---------------------------------------------------------------+-------------------------------------------------------------------------+
| options.transpilation.layout_method (Optional[str])           | Name of layout selection pass. One of ``trivial``, ``dense``,           |
|                                                               | ``noise_adaptive``, ``sabre``.                                          |
+---------------------------------------------------------------+-------------------------------------------------------------------------+
| options.transpilation.routing_method (Optional[str])          | Name of routing pass: ``basic``, ``lookahead``, ``stochastic``,         |
|                                                               | ``sabre``, ``none``.                                                    |
+---------------------------------------------------------------+-------------------------------------------------------------------------+
| options.transpilation.skip_transpilation (bool)               | This option is specific to Qiskit Runtime primitives.                   |
|                                                               | Allows for skipping transpilation entirely. If you use this method,     |
|                                                               | make sure to verify that your circuit in written using the basis gates  |
|                                                               | on the backend you are running on.                                      |
+---------------------------------------------------------------+-------------------------------------------------------------------------+
| options.transpilation.approximation_degree (Optional[float])  | heuristic dial used for circuit approximation                           |
|                                                               | (1.0=no approximation, 0.0=maximal approximation).                      |
|                                                               | Defaults to no approximation for all optimization levels                |
+---------------------------------------------------------------+-------------------------------------------------------------------------+