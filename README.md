# Qiskit Runtime IBM Quantum Client
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

Qiskit Runtime allows authorized users to upload quantum programs. A quantum program, also called a
Qiskit runtime program, is a piece of Python code that takes certain inputs, performs
quantum and classical computation, and returns the processing results. The users can then
invoke these quantum programs by simply passing in the required input parameters.

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
[This guide](https://cloud.ibm.com/docs/quantum-computing?topic=quantum-computing-quickstart)
contains step-by-step instructions on setting this up, including directions to find your
IBM Cloud API key and Cloud Resource Name (CRN), which you will need for authentication.

### Qiskit Runtime on IBM Quantum

Prior to becoming an IBM Cloud service, Qiskit Runtime was offered on IBM Quantum. If you have an
existing IBM Quantum account, you can continue using Qiskit Runtime on IBM Quantum, which is referred to as legacy runtime.

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
from qiskit_ibm_runtime import IBMRuntimeService

# Save an IBM Cloud account.
IBMRuntimeService.save_account(auth="cloud", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")

# Save an IBM Quantum account.
IBMRuntimeService.save_account(auth="legacy", token="MY_IBM_QUANTUM_TOKEN")
```

Once the account is saved on disk, you can instantiate the service without any arguments:

```python
from qiskit_ibm_runtime import IBMRuntimeService
service = IBMRuntimeService()
```

### Loading Account from Environment Variables

Alternatively, the service can discover credentials from environment variables:
```bash
export QISKIT_IBM_TOKEN="MY_IBM_CLOUD_API_KEY"
export QISKIT_IBM_INSTANCE="MY_IBM_CLOUD_CRN"
```

Then instantiate the service without any arguments:
```python
from qiskit_ibm_runtime import IBMRuntimeService
service = IBMRuntimeService()
```

### Enabling Account for Current Session

As another alternative, you can also enable an account just for the current session by instantiating the
service with your credentials.

```python
from qiskit_ibm_runtime import IBMRuntimeService

# For an IBM Cloud account.
cloud_service = IBMRuntimeService(auth="cloud", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")

# For an IBM Quantum account.
legacy_service = IBMRuntimeService(auth="legacy", token="MY_IBM_QUANTUM_TOKEN")
```

## Accessing Qiskit Runtime Programs

### Finding available programs

To list all available programs:

```python
from qiskit_ibm_runtime import IBMRuntimeService
service = IBMRuntimeService()
service.pprint_programs()
```

`pprint_programs()` prints the summary metadata of the first 20 programs visible to you. A program's metadata
consists of its ID, name, description, input parameters, return values, interim results, and
other information that helps you to know more about the program. `pprint_programs(detailed=True, limit=None)`
will print all metadata for all programs visible to you.

### Executing a Program

To run a program, specify the program ID, input parameters, as well as any execution options:

```python
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit_ibm_runtime import IBMRuntimeService

service = IBMRuntimeService()
program_inputs = {
    'circuits': ReferenceCircuits.bell()
}
options = {'backend_name': 'ibmq_qasm_simulator'}
job = service.run(
    program_id="sampler",
    options=options,
    inputs=program_inputs)
print(f"job ID: {job.job_id}")
result = job.result()
```

## Accessing your IBM Quantum backends

A **backend** is a quantum device or simulator capable of running quantum circuits or pulse schedules.

You can query for the backends you have access to. Attributes and methods of the returned instances
provide information, such as qubit counts, error rates, and statuses, of the backends.

```python
from qiskit_ibm_runtime import IBMRuntimeService
service = IBMRuntimeService()

# Display all backends you have access.
print(service.backends())

# Get a specific backend.
backend = service.backend('ibmq_qasm_simulator')
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
