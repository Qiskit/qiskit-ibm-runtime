Manage costs
============

The Standard Plan is not free. Use the information in this topic to help you understand how much you’re paying and how to limit your costs.

Time limits on programs
-----------------------

The maximum execution time for the Sampler primitive is 10000 seconds (2.78 hours). The maximum execution time for the Estimator primitive is 18000 seconds (5 hours).

Additionally, the system limit on the job execution time is 3 hours for a job that is running on a simulator and 8 hours for a job running on a physical system.

How to limit your cost
----------------------

The time your job takes (and therefore, its cost) depends on how many iterations you make in a session and how many shots are run in each iteration. Thus, you can manage your cost by running only as many iterations and shots as you need.

To set cost limits, navigate to the `IBM Cloud Instances page <https://cloud.ibm.com/quantum/instances>`__, then click your instance. You can set these limits:

-  **Instance cost limit**: Specify how much total cost this instance can incur.
-  **Max cost per session**: Specify how much can be spent running jobs in each session.

How to see what you’re being charged
------------------------------------

You can see how much has been spent on each instance’s details page. For more information, see `View the cost <view-cost>`__.

Additionally, you are sent a monthly invoice that provides details about your resource charges. You can check how much has been spent at any time on the `IBM Cloud Billing and usage page <https://cloud.ibm.com/billing>`__.

Set up spending notifications
-----------------------------

You can set up spending notifications to get notified when your account or a particular service reaches a specific spending threshold that you set. For information, see the `IBM Cloud account Type description <https://cloud.ibm.com/docs/account?topic=account-accounts>`__. IBM Cloud spending notifications must be used with other methods of cost management for several reasons:

-  The notifications trigger only *after* cost surpasses the specified limit.
-  Cost is submitted to the billing system hourly. Thus, a long delay might occur between the job submission and the spending notification being sent.
-  The billing system can take multiple days to get information to the invoicing system, which might cause further delay in notifications. For more information about how the IBM Cloud billing system works, see `Setting spending notifications <https://cloud.ibm.com/docs/billing-usage?topic=billing-usage-spending>`__.

Next steps
----------

See `Qiskit Runtime plans <plans>`__ to learn about the plans.
