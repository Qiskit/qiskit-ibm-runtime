---

copyright:
  years: 2021, 2022
lastupdated: "2021-11-05"

keywords: quantum, Qiskit, runtime, near time compute, run qiskit job, qiskit job status

subcollection: quantum-computing

content-type: howto

---

{{site.data.keyword.attribute-definition-list}}


# Run a job
{: #run_job}

This tutorial walks you through the steps to use a program to run a job on an IBM Quantum computer, and return the job status.
{: shortdesc}


## Before you begin
{: #run-program-byb}

You'll need a circuit to submit to the program. To learn how to create circuits by using Qiskit, see the [Circuit basics tutorial](https://qiskit.org/documentation/tutorials/circuits/01_circuit_basics.html){: external}.


## Run the job
{: #run-job-step}
{: step}


You will use the Qiskit Runtime QiskitRuntimeService.run() method, which takes the following parameters:

- program_id: ID of the program to run.
- inputs: Program input parameters. These input values are passed to the runtime program and are dependent on the parameters defined for the program.
- options: Runtime options. These options control the execution environment. Currently, the only available option is backend_name, which is optional. If you do not specify a backend, the job is sent to the least busy device that you have access to.
- result_decoder: Optional class used to decode the job result.

In the following example, we will submit a circuit to the Sampler program.

Use the [Run a job API](/apidocs/quantum-computing#create-job){: external}. Optionally, use [Swagger](https://us-east.quantum-computing.cloud.ibm.com/openapi/#/Jobs/create_job){: external}. You must specify the program ID and can optionally supply parameters and the device to run on. Any other input is ignored. Note the job ID that is returned. You need this information to check the status and view results.

If you do not specify the device, the job is sent to the least busy device that you have access to.

To ensure fairness, there is a maximum execution time for each Qiskit Runtime job. If a job exceeds this time limit, it is forcibly terminated. The maximum execution time is the smaller of 1) the system limit and 2) the `max_execution_time` defined by the program. The system limit is 3 hours for jobs running on a simulator and 8 hours for jobs running on a physical system.
{: note}

## (Optional) Return the job status
{: #return-status}
{: step}

Follow up the Qiskit Runtime QiskitRuntimeService.run() method by running a RuntimeJob method. The run() method returns a RuntimeJob instance, which represents the asynchronous execution instance of the program.

There are several RuntimeJob methods to choose from, including job.status():

Run the [List job details API](/apidocs/quantum-computing#get-job-details-jid){: external}, manually or by using [Swagger](https://us-east.quantum-computing.test.ibm.com/openapi/#/Jobs/get_job_details_jid){: external} to check the job's status.

## Next steps
{: #next-steps}

- [View the results](/docs/quantum-computing?topic=quantum-computing-results).
- View the [API reference](/apidocs/quantum-computing/quantum-computing){: external}.
- Learn about IBM Quantum:
    - [IBM Quantum Computing](https://www.ibm.com/quantum-computing/){: external}
    - [Qiskit](https://qiskit.org/){: external}
