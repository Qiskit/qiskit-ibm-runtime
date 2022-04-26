---

copyright:
  years: 2021, 2022
lastupdated: "2021-11-05"

keywords: quantum, Qiskit, runtime, near time compute

subcollection: quantum-computing

content-type: howto

---

{{site.data.keyword.attribute-definition-list}}


# View final job results
{: #view-final}

This tutorial describes how to review final results after running a job. For an example of running a job, see [Get started with the Estimator primitive](/docs/quantum-computing?topic=quantum-computing-example-estimator) or [Get started with the Sampler primitive](/docs/quantum-computing?topic=quantum-computing-example-sampler).
{: shortdesc}

## Before you begin
{: #before-you-begin-results}

Run your job and note the job ID.

## Check the status
{: #check-job-status-before-results}

After the job completes, you can view the results.

Immediately after running the job, follow up the {{site.data.keyword.qiskit_runtime_notm}} QiskitRuntimeService.run() method by running `job.status()`.

If you ran other jobs since running the job you want to investigate, run `job = service.job(job_id)` then run `job.status()`.

Jobs are also listed on the Jobs page for your quantum service instance.  From the {{site.data.keyword.cloud_notm}} console quantum [Instances page](https://cloud.ibm.com/quantum/instances){: external}, click the name of your instance, then click the Jobs tab.  To see the current status of your job, click the refresh arrow in the upper right corner.

You can optionally run the [List job details API](/apidocs/quantum-computing#get-job-details-jid){: external}, manually or by using [Swagger](https://us-east.quantum-computing.cloud.ibm.com/openapi/#/Jobs/get_job_details_jid){: external} to check the job's status.


## View the results
{: #view-results}


Follow up the {{site.data.keyword.qiskit_runtime_notm}} QiskitRuntimeService.run() method by running `job.result()`.

After the job has completed, you can click the job on the Jobs page to view the result.

Alternatively, run the [list job results API](/apidocs/quantum-computing#get-job-results-jid){: external} ([Swagger link](https://us-east.quantum-computing.cloud.ibm.com/openapi/#/Jobs/get_job_results_jid){: external}).

## Next steps
{: #next-steps}

- View the [API reference](/apidocs/quantum-computing/quantum-computing){: external}.
- Learn about [IBM Quantum Computing](https://www.ibm.com/quantum-computing/){: external}.
