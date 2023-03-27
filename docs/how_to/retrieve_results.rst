Retrieve job results
=================================

You can review job results immediately after a job completes by calling ``job.result()``, but there are also several ways to retrieve your results later.  

After starting your job, a job instance returned.  Run ``job.job_id()`` to get the ID. After the job completes, you can view the results. You can check the status of your job by calling ``job.status()``.

If you ran other jobs since running the job you want to investigate, run ``job = service.job(job_id)`` then run ``job.status()``.

Jobs are also listed on the Jobs page for your quantum service instance:

* From the IBM Cloud console quantum `Instances page <https://cloud.ibm.com/quantum/instances>`__, click the name of your instance, then click the Jobs tab. To see the status of your job, click the refresh arrow in the upper right corner.
* In IBM Quantum platform, open the `Jobs page <https://quantum-computing.ibm.com/jobs>`__.




