---

copyright:
  years: 2021, 2022
lastupdated: "2022-03-14"

keywords: Qiskit Runtime backend, Qiskit Runtime device, Qiskit Runtime simulator, Qiskit Runtime systems

subcollection: quantum-computing

content-type: howto

---

{{site.data.keyword.attribute-definition-list}}


# Choose a backend
{: #choose-backend}

Before running a job, you can optionally choose a backend (a physical quantum system or a simulator) to run on.  If you do not specify one, the job is sent to the least busy device that you have access to.

The Standard plan only allows access to physical quantum systems, while the Lite plan only allows access to simulators.
{: #note}

To find your available backends, run `service.backends()` in Qiskit and note the name of the backend you want to use.  For full details, including available options, see the [Qiskit Runtime API documentation](https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.QiskitRuntimeService.backends.html#qiskit_ibm_runtime.QiskitRuntimeService.backends).

You can also view your available backends by using the [List your devices](/apidocs/quantum-computing#list-devices){: external} API directly or in [Swagger](https://us-east.quantum-computing.cloud.ibm.com/openapi/#/Programs/list-devices){: external}.
