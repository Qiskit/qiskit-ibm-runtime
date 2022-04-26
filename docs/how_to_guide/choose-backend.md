# Choose a backend

Before running a job, you can optionally choose a backend (a physical quantum system or a simulator) to run on.  If you do not specify one, the job is sent to the least busy device that you have access to.

The Standard plan only allows access to physical quantum systems, while the Lite plan only allows access to simulators.

To find your available backends, run `service.backends()` in Qiskit and note the name of the backend you want to use.  For full details, including available options, see the [Qiskit Runtime API documentation](https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.QiskitRuntimeService.backends.html#qiskit_ibm_runtime.QiskitRuntimeService.backends).
