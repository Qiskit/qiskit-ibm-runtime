Set up Terraform for Qiskit Runtime
===================================

If you use Terraform to manage your infrastructure, the `IBM Cloud provider for Terraform <https://cloud.ibm.com/docs/ibm-cloud-provider-for-terraform?topic=ibm-cloud-provider-for-terraform-getting-started>`__ supports provisioning Qiskit Runtime service instances. The generic "ibm_resource_instance" resource is used for that. The following parameters have to be specified:

Provisioning with Terraform
---------------------------

If you use Terraform to manage your infrastructure, the `IBM Cloud provider for Terraform <https://cloud.ibm.com/docs/ibm-cloud-provider-for-terraform?topic=ibm-cloud-provider-for-terraform-getting-started>`__ supports provisioning Qiskit Runtime service instances. The generic "ibm_resource_instance" resource is used for that. The following parameters have to be specified:

-  ``name`` – The name of your service instance.
-  ``service`` – Specify ``quantum-computing`` to provision Qiskit Runtime instances.
-  ``plan`` – Can be ``lite`` or ``paygo-standard``.
-  ``location`` – Currently, this must be ``us-east``.

Optional parameters include:

-  ``resource_group_id`` – Creates the service instance in the specified resource group.
-  ``tags`` – Add tags to the resource.

Example: Creating a Service Instance of Qiskit Runtime
------------------------------------------------------

After the job completes, you can view the results.

1. In your Terraform configuration file, add the following code.  Change the name of the service instance (parameter “name”) and the plan (parameter “plan”) according to your requirements:

     .. code:: 

        resource "ibm_resource_instance" "my-instance" {
                name = "my-instance-name"
                service = "quantum-computing"
                plan = "lite"
                location = "us-east"
        }

   

2. Create a Terraform execution plan.

   .. code:: 

      terraform plan


3. Remove the namespace and re-create it with a new name. Note that this process might take a few minutes to complete.

   .. code:: 

      terraform apply


4. Verify on the `Instances page <https://cloud.ibm.com/quantum/instances>`__ that your service instance has been created.

Qiskit Runtime service instances are IAM managed resources. Access can be shaped through terraform using IAM user policies. See `ibm_iam_user_policy <https://registry.terraform.io/providers/IBM-Cloud/ibm/latest/docs/resources/iam_user_policy>`__ for more details and examples.