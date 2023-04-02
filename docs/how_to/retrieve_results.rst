Retrieve job results
=================================

After submitting your job, a `RuntimeJob <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.RuntimeJob.html#qiskit_ibm_runtime.RuntimeJob>`_ instance is returned. Use the job instance to check the job status or retrieve the results by using these methods: 
- `job.status()` 
- `job.result()` - Job results are available after the job completes.  Therefore, `job.result()` is a blocking call until the job completes.

Retrieve job results at a later time
************************************

Retrieving job results for a specific job at a later time requires the `job ID`, which uniquely identifies the job.  To determine the job ID, call `job.job_id()` after submitting the job.  It is recommended that you save the IDs of jobs you might want to retrieve later.  Call `service.job(<job ID>)` to retrieve a job you previously submitted.  

If you don't have the job ID, or if you want to retrieve multiple jobs at once; including jobs from retired systems, call `service.jobs()` with optional filters instead.  See `QiskitRuntimeService.jobs <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.QiskitRuntimeService.jobs.html>`__.

.. note:: 
  `service.jobs()` returns only Qiskit Runtime jobs. To retrieve other jobs, use `qiskit-ibm-provider <https://qiskit.org/documentation/partners/qiskit_ibm_provider/stubs/qiskit_ibm_provider.IBMBackend.html#qiskit_ibm_provider.IBMBackend>`__ instead.

Example
-------

This example returns the 10 most recent runtime jobs that were run on `my_backend`:

.. code-block:: python
  
  from qiskit_ibm_runtime import QiskitRuntimeService

  # Initialize the account first.
  service = QiskitRuntimeService()

  service.jobs(backend_name=my_backend)

Jobs are also listed on the Jobs page for your quantum service channel:

- IBM Cloud channel: From the IBM Cloud console quantum `Instances page <https://cloud.ibm.com/quantum/instances>`__, click the name of your instance, then click the Jobs tab. To see the status of your job, click the refresh arrow in the upper right corner.
- IBM Quantum channel: In IBM Quantum platform, open the `Jobs page <https://quantum-computing.ibm.com/jobs>`__.




