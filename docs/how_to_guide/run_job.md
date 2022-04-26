# Run a job

This tutorial walks you through the steps to use a program to run a job on an IBM Quantum computer, and return the job status.


## Before you begin

You'll need a circuit to submit to the program. To learn how to create circuits by using Qiskit, see the [Circuit basics tutorial](https://qiskit.org/documentation/tutorials/circuits/01_circuit_basics.html).


## Run the job


You will use the Qiskit Runtime QiskitRuntimeService.run() method, which takes the following parameters:

- program_id: ID of the program to run.
- inputs: Program input parameters. These input values are passed to the runtime program and are dependent on the parameters defined for the program.
- options: Runtime options. These options control the execution environment. Currently, the only available option is backend_name, which is optional. If you do not specify a backend, the job is sent to the least busy device that you have access to.
- result_decoder: Optional class used to decode the job result.

In the following example, we will submit a circuit to the Sampler program.

If you do not specify the device, the job is sent to the least busy device that you have access to.

To ensure fairness, there is a maximum execution time for each Qiskit Runtime job. If a job exceeds this time limit, it is forcibly terminated. The maximum execution time is the smaller of 1) the system limit and 2) the `max_execution_time` defined by the program. The system limit is 3 hours for jobs running on a simulator and 8 hours for jobs running on a physical system.

## (Optional) Return the job status

Follow up the Qiskit Runtime QiskitRuntimeService.run() method by running a RuntimeJob method. The run() method returns a RuntimeJob instance, which represents the asynchronous execution instance of the program.

There are several RuntimeJob methods to choose from, including job.status():
