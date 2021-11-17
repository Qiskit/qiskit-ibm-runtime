# Qiskit IBM Runtime

[![License](https://img.shields.io/github/license/Qiskit/qiskit-ibm-runtime.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)[![Push-Test](https://github.com/Qiskit/qiskit-ibm-runtime/actions/workflows/main.yml/badge.svg)](https://github.com/Qiskit/qiskit-ibm-runtime/actions/workflows/main.yml)[![](https://img.shields.io/github/release/Qiskit/qiskit-ibm-runtime.svg?style=popout-square)](https://github.com/Qiskit/qiskit-ibm-runtime/releases)[![](https://img.shields.io/pypi/dm/qiskit-ibm-runtime.svg?style=popout-square)](https://pypi.org/project/qiskit-ibm-runtime/)

**Qiskit** is an open-source SDK for working with quantum computers at the level of circuits, algorithms, and application modules.

This project allows accessing the **[IBM Quantum]** systems and simulators.

## Installation

You can install this package using pip:

```bash
pip install qiskit-ibm-runtime
```

## Legacy Setup

1. Create an IBM Quantum account or log in to your existing account by visiting the [IBM Quantum login page].

1. Copy (and/or optionally regenerate) your API token from your
   [IBM Quantum account page].

1. Take your token from step 2, here called `MY_API_TOKEN`, and save it by calling `IBMRuntimeService.save_account()`:

   ```python
   from qiskit_ibm_runtime import IBMRuntimeService
   IBMRuntimeService.save_account(token='MY_API_TOKEN')
   ```

   The command above stores your credentials locally in a configuration file called `qiskitrc`. By default, this file is located in `$HOME/.qiskit`, where `$HOME` is your home directory.
   Once saved you can then instantiate the provider like below and access the backends:

   ```python
   from qiskit_ibm_runtime import IBMRuntimeService
   service = IBMRuntimeService()

   # display current supported backends
   print(service.backends())

   # get IBM's simulator backend
   simulator_backend = service.get_backend('ibmq_qasm_simulator')
   ```

### Load Account from Environment Variables
Alternatively, the service can discover credentials from environment variables:
```bash
export QISKIT_IBM_RUNTIME_API_TOKEN='MY_API_TOKEN'
```

Then instantiate the service without any arguments and access the backends:
```python
from qiskit_ibm_runtime import IBMRuntimeService
service = IBMRuntimeService()
```

### Enable Account for Current Session
As another alternative, you can also enable an account just for the current session by instantiating the service with the token.

```python
from qiskit_ibm_runtime import IBMRuntimeService
service = IBMRuntimeService(token='MY_API_TOKEN')
```

## Next Steps

Now you're set up and ready to check out some of the tutorials.
- [Qiskit Runtime]

## Contribution Guidelines

If you'd like to contribute to Qiskit IBM Runtime, please take a look at our
[contribution guidelines]. This project adheres to Qiskit's [code of conduct].
By participating, you are expected to uphold to this code.

We use [GitHub issues] for tracking requests and bugs. Please use our [slack]
for discussion and simple questions. To join our Slack community use the
invite link at [Qiskit.org]. For questions that are more suited for a forum we
use the `Qiskit` tag in [Stack Exchange].

## Authors and Citation

The Qiskit IBM Runtime is the work of [many people] who contribute to the
project at different levels. If you use Qiskit, please cite as per the included
[BibTeX file].

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
[Qiskit Runtime]: https://github.com/Qiskit-Partners/qiskit-runtime/tree/main/tutorials
[many people]: https://github.com/Qiskit/qiskit-ibm-runtime/graphs/contributors
[BibTeX file]: https://github.com/Qiskit/qiskit/blob/master/Qiskit.bib
[Apache License 2.0]: https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/LICENSE.txt
