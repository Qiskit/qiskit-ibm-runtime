Retrieve jobs from a retired system
===================================

See a list of retired systems on `this page <../retired.html>`__.

To retrieve jobs that were not submitted by using Qiskit Runtime, use `qiskit-ibm-provider <https://qiskit.org/documentation/partners/qiskit_ibm_provider/stubs/qiskit_ibm_provider.IBMBackend.html#qiskit_ibm_provider.IBMBackend>` instead. 

To retrieve Qiskit Runtime jobs from a retired system, use code similar to the following:


.. code-block:: python
  
  from qiskit_ibm_runtime import QiskitRuntimeService

  provider = IBMProvider(instance="hub/group/project")

  #If you want to retrieve a list of jobs
  jobs = provider.backend.jobs(backend_name=<backend_name>)

  #If you want to retrieve a specific job you have the id for 
  job = provider.backend.retrieve_job(<job_id>)

The `provider.backend.jobs()` method also has more filtering options. Learn more from the `IBMBackend API documentation. <https://qiskit.org/documentation/partners/qiskit_ibm_provider/stubs/qiskit_ibm_provider.IBMBackend.html#qiskit_ibm_provider.IBMBackend>`__