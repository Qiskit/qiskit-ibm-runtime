Retrieve job results
=================================

After submitting your job, a `job instance` is returned. Use the job instance to check the job status or retrieve the results by using these commands: 
- `job.status()` 
- `job.result()` - Job results are available after the job completes.  Therefore, `job.result()` is a blocking call until the job completes.

Retrieve job results at a later time
************************************

Retrieving job results for a specific job at a later time requires the `job ID`, which uniquely identifies the job.  To determine the job ID, call `job.job_id()` after submitting the job.  It is recommended that you save the IDs of jobs you might want to retrieve later.  Call `QiskitRuntimeService.job(<job ID>)` to retrieve a job you previously submitted.  

If you don't have the job ID, or if you want to retrieve multiple jobs at once; including jobs from retired systems, call `QiskitRuntimeService.jobs()` with optional filters instead.  See `QiskitRuntimeService.jobs <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.QiskitRuntimeService.jobs.html>`__.

.. note:: 
  `QiskitRuntimeService.jobs()` returns only Qiskit Runtime jobs. 

Jobs are also listed on the Jobs page for your quantum service channel:

- IBM Cloud channel: From the IBM Cloud console quantum `Instances page <https://cloud.ibm.com/quantum/instances>`__, click the name of your instance, then click the Jobs tab. To see the status of your job, click the refresh arrow in the upper right corner.
- IBM Quantum channel: In IBM Quantum platform, open the `Jobs page <https://quantum-computing.ibm.com/jobs>`__.




