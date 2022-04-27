# Run a program

This guide shows you how to run a runtime program.

You can use the [QiskitRuntimeService.run()](https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.QiskitRuntimeService.run.html#qiskit_ibm_runtime.QiskitRuntimeService.run) method to invoke a runtime program. This method takes the following parameters:

- `program_id`: ID of the program to run.
- `inputs`: Program input parameters. These input values are passed to the runtime program.
- `options`: Runtime options. These options control the execution environment. Currently the only available option is `backend_name`, which is required for IBM Quantum but it's optional for IBM Cloud. If you do not specify one, the job is sent to the least busy device that you have access to.
- `callback`: Callback function to be invoked for any interim results and final result. The callback function will receive two positional parameters: job ID and result.
- `result_decoder`: Optional class used to decode the job result.

Here is an example of running the `hello-world` program.

```python
# Specify the program inputs here.
program_inputs = {"iterations": 3}

# Specify the backend name.
options = {"backend_name": "ibmq_qasm_simulator"}

job = service.run(
    program_id="hello-world",
    inputs=program_inputs,
    options=options
)

# Printing the job ID in case we need to retrieve it later.
print(f"job id: {job.job_id}")

# Get the job result - this is blocking and control may not return immediately.
result = job.result()
print(result)
```
