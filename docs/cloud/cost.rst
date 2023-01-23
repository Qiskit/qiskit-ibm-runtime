Manage costs
============

The Standard plan is not free. Use the information in this topic to help you understand how much you’re paying and how to limit your costs.

Time limits on programs
-----------------------

The maximum execution time for the Sampler primitive is 10000 seconds (2.78 hours). The maximum execution time for the Estimator primitive is 18000 seconds (5 hours).

Additionally, the system limit on the job execution time is 3 hours for a job that is running on a simulator and 8 hours for a job running on a physical system.

How to limit your cost
----------------------

The time your job takes (and therefore, its cost) depends on how many iterations you make in a session and how many shots are run in each iteration. Thus, you can manage your cost by running only as many iterations and shots as you need.

Additionally, an instance administrator can limit how much is spent. To set cost limits, navigate to the `IBM Cloud Instances page <https://cloud.ibm.com/quantum/instances>`__, then click your instance. You can set the **Instance cost limit**. This limits the total cost that jobs run with this instance can incur.  After the instance reaches the specified number of seconds, no further jobs can be run and no more cost is incurred.

.. note::
   The instance cost limit is always specified in US dollars (USD), then converted to runtime seconds.  However, for monthly billing purposes, you are charged in your local currency, specified on your IBM Cloud account. Due to currency conversion, the cost for `X` runtime seconds is different when calculated in USD than in your local currency.  As a result, if your local currency is not USD, the total amount charged for the number of seconds specified in this field could vary from the dollar amount you specify.

What happens when the cost limit is reached
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the instance's cost limit is reached, the currently running job is stopped.  Its status is set to `Cancelled` with a reason of `Ran too long`. Any available partial results are kept. 

No further jobs can be submitted by using this instance until the cost limit is increased. 


How to see what you’re being charged
------------------------------------

You are sent a monthly invoice that provides details about your resource charges. You can check how much has been spent at any time on the `IBM Cloud Billing and usage page <https://cloud.ibm.com/billing>`__.

Additionally, you can determine cost per instance or per job at any time.

View instance cost
^^^^^^^^^^^^^^^^^^^^^

To determine how much has been billed to an instance during the current billing cycle, from the `Instances page <https://cloud.ibm.com/quantum/instances>`__, click the instance to open its details page.

These are the fields relevant to cost:

- **Billing cycle QR usage**: The amount of quantum runtime used by this instance during the current billing cycle
- **Billing cycle cost**: The total cost of running jobs during the current billing cycle
- **Total QR usage**: The amount of quantum runtime used by this instance since it was created
- **Total cost**: The total cost of running jobs on this instance since it was created

You can view your billing cycle on the `Billing and usage page <https://cloud.ibm.com/billing>`__.

View job cost
^^^^^^^^^^^^^^

To determine how much has been billed to each job associated with an instance, from the `Instances page <https://cloud.ibm.com/quantum/instances>`__, click the instance to open its details page. Next, on the left side, click Jobs.

These are the columns relevant to cost:

- **QR usage**: The amount of quantum runtime used by this job
- **Cost**: The total cost of running this job


Set up spending notifications
-----------------------------

You can set up spending notifications to get notified when your account or a particular service reaches a specific spending threshold that you set. For information, see the `IBM Cloud account Type description <https://cloud.ibm.com/docs/account?topic=account-accounts>`__. IBM Cloud spending notifications must be used with other methods of cost management for several reasons:

- The notifications trigger only *after* cost surpasses the specified limit.
- Cost is submitted to the billing system hourly. Thus, a long delay might occur between the job submission and the spending notification being sent.
- The billing system can take multiple days to get information to the invoicing system, which might cause further delay in notifications. For more information about how the IBM Cloud billing system works, see `Setting spending notifications <https://cloud.ibm.com/docs/billing-usage?topic=billing-usage-spending>`__.

Next steps
----------

See `Qiskit Runtime plans <plans.html>`__ to learn about the plans.
