Learning about Qiskit Runtime architecture and workload isolation
=================================================================


Qiskit Runtime jobs run in individual containers in an internal Kubernetes cluster to isolate jobs from any other activities of other users. Jobs are not shared or visible between service instances. However, all users that can access a service instance can see that instance’s jobs, or submit jobs the account owner might be charged for.
 

Restricting Access to service instances
---------------------------------------

With Qiskit Runtime, you can create service instances that are IAM-managed resources. Accordingly, IAM-based access control can be used for these service instances.
User access to Qiskit Runtime service instances can be configured through different mechanisms:
-  Resource groups can be used to group service instances. This lets you manage access permissions based on resource group assignment.
-  Access groups can be used to assign access to individual service instances. Service IDs (with their API keys) can be assigned to these access groups.
-  IAM tags can be used to categorize service instances and use these tags through access groups.
