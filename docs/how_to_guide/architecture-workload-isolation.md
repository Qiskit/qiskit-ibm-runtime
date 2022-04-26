---

copyright:
  years: 2022
lastupdated: "2022-03-28"

keywords: public isolation for Qiskit Runtime, compute isolation for Qiskit Runtime, Qiskit Runtime architecture, workload isolation in Qiskit Runtime

---

{{site.data.keyword.attribute-definition-list}}

# Learning about Qiskit Runtime workload isolation
{: #compute-isolation-runtime}

<!-- The title of your H1 should be Learning about Qiskit Runtime architecture and workload isolation, where _service-name_ is the non-trademarked short version keyref, but the first occurrence in your topic is the trademarked version. Include your service name as a search keyword at the top of your Markdown file. See the example keywords above. -->

Qiskit Runtime jobs run in individual containers in an internal Kubernetes cluster to isolate jobs from any other activities of other users. Jobs are not shared or visible between service instances. However, all users that can access a service instance can see that instance’s jobs, or submit jobs the account owner may be charged for.
{: shortdesc}

## Restricting Access to service instances
{: #workload-isolation-runtime}

With Qiskit Runtime, you can create service instances that are IAM-managed resources. Accordingly, IAM-based access control can be used for these service instances.
User access to Qiskit Runtime service instances can be configured through different mechanisms:
-	Resource groups can be used to group service instances. This allows you to manage access permissions based on resource group assignment.
-	Access groups can be used to assign access to individual service instances.  Service IDs (with their API keys) can be assigned to these access groups.
-	IAM tags can be used to categorize service instances and leverage these tags through access groups.
