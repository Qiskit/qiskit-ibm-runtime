---

copyright:
  years: 2022
lastupdated: "2022-03-28"

keywords: quantum, Qiskit, runtime, near time compute, terraform

subcollection: quantum-computing

content-type: howto

---

{{site.data.keyword.attribute-definition-list}}


# Set up Terraform for Qiskit Runtime
{: #setup-terraform}

If you use Terraform to manage your infrastructure, the [IBM Cloud provider for Terraform]( https://cloud.ibm.com/docs/terraform?topic=terraform-getting-started) supports provisioning Qiskit Runtime service instances. The generic “ibm_resource_instance” resource is used for that. The following parameters have to be specified:
{: shortdesc}

## Provisioning with Terraform
{: #Provisioning-with-Terraform}

If you use Terraform to manage your infrastructure, the [IBM Cloud provider for Terraform]( https://cloud.ibm.com/docs/terraform?topic=terraform-getting-started) supports provisioning Qiskit Runtime service instances. The generic “ibm_resource_instance” resource is used for that. The following parameters have to be specified:

-	`name` – The name of your service instance.
-	`service` – Specify `quantum-computing` to provision Qiskit Runtime instances.
-	`plan` – Can be `lite` or `paygo-standard`.
-	`location` – Currently, this must be `us-east`.

Optional parameters include:

-	`resource_group_id` – Creates the service instance in the specified resource group.
-	`tags` – Add tags to the resource.


## Example: Creating a Service Instance of Qiskit Runtime
{: #example}

After the job completes, you can view the results.

1. In your Terraform configuration file, add the following code:

   ```terraform
   resource "ibm_resource_instance" "my-instance" {
             name = "my-instance-name"
             service = "quantum-computing"
             plan = "lite"
             location = "us-east"
   }
   ```
   {: codeblock}

   Change the name of the service instance (parameter “name”) and the plan (parameter “plan”) according to your requirements.
2. Create a Terraform execution plan.  

   ```terraform
   terraform plan
   ```
   {: codeblock}

3. Remove the namespace and re-create it with a new name. Note that this process might take a few minutes to complete.

   ```terraform
   terraform apply
   ```
   {: codeblock}

4. Verify on the [Instances page](https://cloud.ibm.com/quantum/instances){: external} that your service instance has been created.

Qiskit Runtime service instances are IAM managed resources. Access can be shaped through terraform using IAM user policies. See [ibm_iam_user_policy](https://registry.terraform.io/providers/IBM-Cloud/ibm/latest/docs/resources/iam_user_policy){: external} for more details and examples.
