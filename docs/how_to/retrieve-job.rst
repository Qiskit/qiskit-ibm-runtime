Retrieve jobs from a retired system
===================================

See a list of retired systems on `this page <../retired.html>`__.

To retrieve jobs from a retired system, you can use code similar to this:


.. code-block:: python
  
  from qiskit import IBMQ
  IBMQ.load_account()  #If credentials have been saved already

  provider = IBMQ.get_provider(<hub>, <group>, <project>)

  #If you want to retrieve a list of jobs
  jobs = provider.backend.jobs(backend_name=<backend_name>)

  #If you want to retrieve a specific job you have the id for
  job = provider.backend.retrieve_job(<job_id>)

The `provider.backend.jobs()` method also has more filtering options. Learn more `here. <https://qiskit.org/documentation/stubs/qiskit.providers.ibmq.IBMQBackend.jobs.html>`__