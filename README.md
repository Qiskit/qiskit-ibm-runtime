# Qiskit IBM Provider

[![License](https://img.shields.io/github/license/Qiskit-Partners/qiskit-ibm.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)[![Push-Test](https://github.com/Qiskit-Partners/qiskit-ibm/actions/workflows/main.yml/badge.svg)](https://github.com/Qiskit-Partners/qiskit-ibm/actions/workflows/main.yml)[![](https://img.shields.io/github/release/Qiskit-Partners/qiskit-ibm.svg?style=popout-square)](https://github.com/Qiskit-Partners/qiskit-ibm/releases)[![](https://img.shields.io/pypi/dm/qiskit-ibm.svg?style=popout-square)](https://pypi.org/project/qiskit-ibm/)

**Qiskit** is an open-source SDK for working with quantum computers at the level of circuits, algorithms, and application modules.

This project contains a provider that allows accessing the **[IBM Quantum]**
systems and simulators.

## Migrating
If you are migrating from `qiskit-ibmq-provider` please follow the instructions in the [migration guide].

## Installation

You can install the provider using pip:

```bash
pip install qiskit-ibm
```

## Provider Setup

1. Create an IBM Quantum account or log in to your existing account by visiting the [IBM Quantum login page].

1. Copy (and/or optionally regenerate) your API token from your
   [IBM Quantum account page].

1. Take your token from step 2, here called `MY_API_TOKEN`, and save it by calling `IBMProvider.save_account()`:

   ```python
   from qiskit_ibm import IBMProvider
   IBMProvider.save_account(token='MY_API_TOKEN')
   ```

   The command above stores your credentials locally in a configuration file called `qiskitrc`. By default, this file is located in `$HOME/.qiskit`, where `$HOME` is your home directory.
   Once saved you can then instantiate the open access provider (`hub='ibm-q', group='open', project='main'`) like below and access the backends:

   ```python
   from qiskit_ibm import IBMProvider
   provider = IBMProvider()

   # display current supported backends
   print(provider.backends())

   # get IBM's simulator backend
   simulator_backend = provider.get_backend('ibmq_qasm_simulator')
   ```

   To see a list of providers available to your account, use the `IBMProvider.providers()` class method:

   ```python
   from qiskit_ibm import IBMProvider
   IBMProvider.providers()

   # [<IBMProvider(hub='ibm-q', group='open', project='main')>,
   #  <IBMProvider(hub='ibm-q', group='test', project='default')>]
   ```

   To access a different provider you can do:

   ```python
   from qiskit_ibm import IBMProvider
   provider = IBMProvider(hub='ibm-q', group='test', project='default')
   ```

   where `hub='ibm-q', group='test', project='default'` is a sample premium provider.

### Load Account from Environment Variables
Alternatively, the IBM Provider can discover credentials from environment variables:
```bash
export QISKIT_IBM_API_TOKEN='MY_API_TOKEN'
export QISKIT_IBM_API_URL='https://auth.quantum-computing.ibm.com/api'
export QISKIT_IBM_HUB='ibm-q'
export QISKIT_IBM_GROUP='test'
export QISKIT_IBM_PROJECT='default'
```

Then instantiate the provider without any arguments and access the backends:
```python
from qiskit_ibm import IBMProvider
provider = IBMProvider()
```

### Enable Account for Current Session
As another alternative, you can also enable an account just for the current session by instantiating the provider with the token and hub/group/project.

```python
from qiskit_ibm import IBMProvider
provider = IBMProvider(token='MY_API_TOKEN', hub='ibm-q', group='test', project='default')
```

## Contribution Guidelines

If you'd like to contribute to IBM Quantum Provider, please take a look at our
[contribution guidelines]. This project adheres to Qiskit's [code of conduct].
By participating, you are expect to uphold to this code.

We use [GitHub issues] for tracking requests and bugs. Please use our [slack]
for discussion and simple questions. To join our Slack community use the
invite link at [Qiskit.org]. For questions that are more suited for a forum we
use the `Qiskit` tag in [Stack Exchange].

## Next Steps

Now you're set up and ready to check out some of the other examples from our
[Qiskit Tutorial] repository.

## Authors and Citation

The Qiskit IBM Quantum Provider is the work of [many people] who contribute to the
project at different levels. If you use Qiskit, please cite as per the included
[BibTeX file].

## License

[Apache License 2.0].


[IBM Quantum]: https://www.ibm.com/quantum-computing/
[IBM Quantum login page]:  https://quantum-computing.ibm.com/login
[IBM Quantum account page]: https://quantum-computing.ibm.com/account
[contribution guidelines]: https://github.com/Qiskit-Partners/qiskit-ibm/blob/main/CONTRIBUTING.md
[code of conduct]: https://github.com/Qiskit-Partners/qiskit-ibm/blob/main/CODE_OF_CONDUCT.md
[GitHub issues]: https://github.com/Qiskit-Partners/qiskit-ibm/issues
[slack]: https://qiskit.slack.com
[Qiskit.org]: https://qiskit.org
[Stack Exchange]: https://quantumcomputing.stackexchange.com/questions/tagged/qiskit
[Qiskit Tutorial]: https://github.com/Qiskit/qiskit-tutorial
[many people]: https://github.com/Qiskit-Partners/qiskit-ibm/graphs/contributors
[BibTeX file]: https://github.com/Qiskit/qiskit/blob/master/Qiskit.bib
[Apache License 2.0]: https://github.com/Qiskit-Partners/qiskit-ibm/blob/main/LICENSE.txt
[migration guide]: https://github.com/Qiskit-Partners/qiskit-ibm/blob/main/MIGRATING.md
