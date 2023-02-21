# Qiskit Runtime IBM Client
[![License](https://img.shields.io/github/license/Qiskit/qiskit-ibm-runtime.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/Qiskit/qiskit-ibm-runtime/actions/workflows/ci.yml/badge.svg)](https://github.com/Qiskit/qiskit-ibm-runtime/actions/workflows/ci.yml)
[![](https://img.shields.io/github/release/Qiskit/qiskit-ibm-runtime.svg?style=popout-square)](https://github.com/Qiskit/qiskit-ibm-runtime/releases)
[![](https://img.shields.io/pypi/dm/qiskit-ibm-runtime.svg?style=popout-square)](https://pypi.org/project/qiskit-ibm-runtime/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage Status](https://coveralls.io/repos/github/Qiskit/qiskit-ibm-runtime/badge.svg?branch=main)](https://coveralls.io/github/Qiskit/qiskit-ibm-runtime?branch=main)


**Qiskit** is an open-source SDK for working with quantum computers at the level of circuits, algorithms, and application modules.

**Qiskit Runtime** is a new architecture offered by IBM Quantum that streamlines quantum computations.
It is designed to use classical compute resources to execute quantum circuits with more efficiency on quantum processors.

Using Qiskit Runtime, for example, a research team at IBM Quantum was able to achieve 120x speed
up in their lithium hydride simulation. For more information, see the
[IBM Research blog](https://research.ibm.com/blog/120x-quantum-speedup).

This module provides the interface to access Qiskit Runtime.

## Installation

You can install this package using pip:

```bash
pip install qiskit-ibm-runtime
```

## Account Setup

### Qiskit Runtime on IBM Cloud

Qiskit Runtime is now part of the IBM Quantum Services on IBM Cloud. To use this service, you'll
need to create an IBM Cloud account and a quantum service instance.
[This guide](https://cloud.ibm.com/docs/quantum-computing?topic=quantum-computing-get-started)
contains step-by-step instructions on setting this up, including directions to find your
IBM Cloud API key and Cloud Resource Name (CRN), which you will need for authentication.

### Qiskit Runtime on IBM Quantum

Prior to becoming an IBM Cloud service, Qiskit Runtime was offered on IBM Quantum. If you have an
existing IBM Quantum account, you can continue using Qiskit Runtime on IBM Quantum.

You will need your IBM Quantum API token to authenticate with the Qiskit Runtime service:

1. Create an IBM Quantum account or log in to your existing account by visiting the [IBM Quantum login page].

1. Copy (and optionally regenerate) your API token from your
   [IBM Quantum account page].

### Saving Account on Disk

Once you have the account credentials, you can save them on disk, so you won't have to input
them each time. The credentials are saved in the `$HOME/.qiskit/qiskit-ibm.json` file, where `$HOME` is your home directory.

| :warning: Account credentials are saved in plain text, so only do so if you are using a trusted device. |
|:---------------------------|

 ```python
from qiskit_ibm_runtime import QiskitRuntimeService

# Save an IBM Cloud account.
QiskitRuntimeService.save_account(channel="ibm_cloud", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")

# Save an IBM Quantum account.
QiskitRuntimeService.save_account(channel="ibm_quantum", token="MY_IBM_QUANTUM_TOKEN")
```

Once the account is saved on disk, you can instantiate the service without any arguments:

```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
```

### Loading Account from Environment Variables

Alternatively, the service can discover credentials from environment variables:
```bash
export QISKIT_IBM_TOKEN="MY_IBM_CLOUD_API_KEY"
export QISKIT_IBM_INSTANCE="MY_IBM_CLOUD_CRN"
export QISKIT_IBM_CHANNEL="ibm_cloud"
```

Then instantiate the service without any arguments:
```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
```

### Enabling Account for Current Python Session

As another alternative, you can also enable an account just for the current session by instantiating the
service with your credentials.

```python
from qiskit_ibm_runtime import QiskitRuntimeService

# For an IBM Cloud account.
ibm_cloud_service = QiskitRuntimeService(channel="ibm_cloud", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")

# For an IBM Quantum account.
ibm_quantum_service = QiskitRuntimeService(channel="ibm_quantum", token="MY_IBM_QUANTUM_TOKEN")
```

## Qiskit Runtime Session

A Qiskit Runtime **session** allows you to group a collection of iterative calls to the quantum computer. A session is started when the first job within the session is started. Subsequent jobs within the session are prioritized by the scheduler to minimize artificial delay within an iterative algorithm. Data used within a session, such as transpiled circuits, is also cached to avoid unnecessary overhead.

You can use the [`qiskit_ibm_runtime.Session`](https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/session.py) class to start a
session. You are encouraged to start a session as a context manager, to ensure the session is automatically closed upon exit. There are some examples in the sections below.

## Primitives

**Primitives** are prebuilt programs that provide a simplified interface for defining near-time quantum-classical workloads required to efficiently build and customize applications. The initial release of Qiskit Runtime includes two primitives: ``Estimator`` and ``Sampler``. They perform foundational quantum computing tasks and act as an entry point to the Qiskit Runtime service.

There are several different options you can specify when calling the primitive programs. See [`qiskit_ibm_runtime.Options`](https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/options.py#L103) class for more information.

### Sampler

This is a program that takes a list of user circuits as an input and generates an error-mitigated readout of quasi-probabilities. This provides users a way to better evaluate shot results using error mitigation and enables them to more efficiently evaluate the possibility of multiple relevant data points in the context of destructive interference.

To invoke the `Sampler` primitive within a session:

```python
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Options, Sampler
from qiskit import QuantumCircuit

service = QiskitRuntimeService()
options = Options(optimization_level=1)
options.execution.shots = 1024  # Options can be set using auto-complete.

bell = QuantumCircuit(2)
bell.h(0)
bell.cx(0, 1)
bell.measure_all()

with Session(service=service, backend="ibmq_qasm_simulator") as session:
    sampler = Sampler(session=session, options=options)
    job = sampler.run(circuits=bell)
    print(f"Job ID is {job.job_id()}")
    print(f"Job result is {job.result()}")

    # You can make additional calls to Sampler and/or Estimator.
```

### Estimator

This is a program that takes circuits and observables to evaluate expectation values and variances for a given parameter input. This primitive allows users to efficiently calculate and interpret expectation values of quantum operators required for many algorithms.

To invoke the `Estimator` primitive within a session:

```python
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Options, Estimator
from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp

service = QiskitRuntimeService()
options = Options(optimization_level=1)
options.execution.shots = 1024  # Options can be set using auto-complete.

psi1 = RealAmplitudes(num_qubits=2, reps=2)
H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
theta1 = [0, 1, 1, 2, 3, 5]

with Session(service=service, backend="ibmq_qasm_simulator") as session:
    estimator = Estimator(session=session, options=options)

    # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
    job = estimator.run(circuits=[psi1], observables=[H1], parameter_values=[theta1])
    print(f"Job ID is {job.job_id()}")
    print(f"Job result is {job.result()}")

    # You can make additional calls to Sampler and/or Estimator.
```

## Accessing Qiskit Runtime Programs

In addition to the primitives, there are other Qiskit Runtime programs that you can call directly. These programs, however, don't have special class wrappers.

### Finding available programs

To list all available programs:

```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
service.pprint_programs()
```

`pprint_programs()` prints the summary metadata of the first 20 programs visible to you. A program's metadata
consists of its ID, name, description, input parameters, return values, interim results, and
other information that helps you to know more about the program. `pprint_programs(detailed=True, limit=None)`
will print all metadata for all programs visible to you.

### Executing a Program

To run a program, specify the program ID, input parameters, as well as any execution options:

```python
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()
program_inputs = {
    'iterations': 1
}
options = {'backend': 'ibmq_qasm_simulator'}
job = service.run(
    program_id="hello-world",
    options=options,
    inputs=program_inputs)
print(f"job ID: {job.job_id()}")
result = job.result()
```

## Accessing your IBM Quantum backends

A **backend** is a quantum device or simulator capable of running quantum circuits or pulse schedules.

You can query for the backends you have access to. Attributes and methods of the returned instances
provide information, such as qubit counts, error rates, and statuses, of the backends.

```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()

# Display all backends you have access.
print(service.backends())

# Get a specific backend.
backend = service.backend('ibmq_qasm_simulator')

# Print backend coupling map.
print(backend.coupling_map)
```

## Next Steps

Now you're set up and ready to check out some of the [tutorials].

## Contribution Guidelines

If you'd like to contribute to qiskit-ibm-runtime, please take a look at our
[contribution guidelines]. This project adheres to Qiskit's [code of conduct].
By participating, you are expected to uphold to this code.

We use [GitHub issues] for tracking requests and bugs. Please use our [slack]
for discussion and simple questions. To join our Slack community use the
invite link at [Qiskit.org]. For questions that are more suited for a forum we
use the `Qiskit` tag in [Stack Exchange].

## License

[Apache License 2.0].


[IBM Quantum]: https://www.ibm.com/quantum-computing/
[IBM Quantum login page]:  https://quantum-computing.ibm.com/login
[IBM Quantum account page]: https://quantum-computing.ibm.com/account
[contribution guidelines]: https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/CONTRIBUTING.md
[code of conduct]: https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/CODE_OF_CONDUCT.md
[GitHub issues]: https://github.com/Qiskit/qiskit-ibm-runtime/issues
[slack]: https://qiskit.slack.com
[Qiskit.org]: https://qiskit.org
[Stack Exchange]: https://quantumcomputing.stackexchange.com/questions/tagged/qiskit
[many people]: https://github.com/Qiskit/qiskit-ibm-runtime/graphs/contributors
[BibTeX file]: https://github.com/Qiskit/qiskit/blob/master/Qiskit.bib
[Apache License 2.0]: https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/LICENSE.txt
[tutorials]: https://github.com/Qiskit/qiskit-ibm-runtime/tree/main/docs/tutorials
