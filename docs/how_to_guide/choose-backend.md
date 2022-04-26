# Choose a backend

This guide shows you how to specify the backend and how to see the list of available backends (physical quantum systems or simulators) and apply filters to choose a backend to run a runtime programs.

## Specify the backend

You can specify the backend to run a runtime program by specifying the `backend_name` option and pass to the program.

```python
options = {"backend_name": "ibmq_qasm_simulator"}
job = service.run(
    program_id="hello-world",
    options=options
)
```

For IBM Quantum, specifying the backend is required.

For IBM Cloud, specifying the backend is optional. If you do not specify one, the job is sent to the least busy device that you have access to.

Below you can find instructions on how to see the list of available backends and apply filters to choose a backend.


## See the list of available backends

You can see the list of available backends by calling `QiskitRuntimeService.backends()`.

```python
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()
service.backends()
```

## Apply filters for choosing backends

You can apply filters for choosing backends including the following options. See [the API reference](https://qiskit.org/documentation/partners/qiskit_ibm_runtime/stubs/qiskit_ibm_runtime.QiskitRuntimeService.backends.html#qiskit_ibm_runtime.QiskitRuntimeService.backends) for more details.

### Filter by backend name

You can choose a backend by specifying the backend name. Here is an example to get the `ibmq_qasm_simulator` backend.

```python
service.backends(name='ibmq_qasm_simulator')
```

### Filter by minimum number of qubits

You can filter backends by specifying the minimum number of qubits. Here is an example to get backends that has at least 20 qubits.

```python
service.backends(min_num_qubits=20)
```

### Filter by IBM Quantum provider hub/group/project

If you are accessing Qiskit Runtime service from IBM Quantum platform, you can filter backends using the `hub/group/project` format of IBM Quantum provider. See [IBM Quantum account page](https://quantum-computing.ibm.com/account) for the list of providers you have access to. Here is an example to get backends that are availabe to the default IBM Quantum open provider.

```python
service.backends(instance='ibm-q/open/main')
```

### Filter by backend configuration or status

You can specify ``True``/``False`` criteria in the backend configuration or status using optional keyword arguments `**kwargs`. Here is an example to get the operational real backends.

```python
service.backends(simulator=False, operational=True)
```

### Filter by complex filters

You can also apply more complex filters such as lambda functions. Here is an example to get backends that has quantum volume larger than 16.

```python
service.backends(
    simulator=False,
    filters=lambda b: b.configuration().quantum_volume > 16)
```
