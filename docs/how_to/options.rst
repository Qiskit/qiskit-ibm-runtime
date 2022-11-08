Configure primitive program options
========================================

When calling the primitives, you can pass in options, as shown in the line "estimator = Estimator(options=options)" in the following code example:

.. code-block:: python
    
    from qiskit_ibm_runtime import QiskitRuntimeService, Session, Estimator, Options

    service = QiskitRuntimeService()
    options = Options(optimization_level=1)

    with Session(service=service, backend="ibmq_qasm_simulator"):
    estimator = Estimator(options=options)

The most commonly used options are for error suppression and mitigation, which are described in this topic. For a full list of available options, see the `Options API reference <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.options.Options.html#qiskit_ibm_runtime.options.Options>`__.

Overview of error suppression and mitigation
--------------------------------------------

No computing platform is perfect, and because quantum computers are such new and complex technology, we have to find new ways of dealing with these imperfections.  There are several possible causes for errors: “noise” - disturbances in the physical environment, and “bit errors”, which cause the qubit's value or phase to change.  IBM builds redundancy into the hardware to ensure that even if some qubits error out, an accurate result is still returned.  However, we can further address errors by using error suppression and error mitigation techniques  These strategies make use of pre- and post-processing to improve the quality of the results produced for the input circuit. 

* **Error suppression**: Techniques that optimize and transform your circuit at the point of compilation to minimize errors. This is the most basic error handling technique.  Error suppression typically results in some classical pre-processing overhead to your overall runtime.

Primitives let you employ error suppression techniques by setting the optimization level ("optimization_level" option) and by choosing advanced transpilation options.  See `<error-suppression.html>`__ for details. 

* **Error mitigation**: Techniques that allow users to mitigate circuit errors by modeling the device noise at the time of execution. This typically results in quantum pre-processing overhead related to model training, and classical post-processing overhead to mitigate errors in the raw results by using the generated model.

The error mitigation techniques built in to primitives are advanced resilience options.   To specify these options, use the "resilience_level" when submitting your job.  See `<error-mitigation.html>`__ for details. 


