# Qiskit Runtime IBM Client
[![License](https://img.shields.io/github/license/Qiskit/qiskit-ibm-runtime.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/Qiskit/qiskit-ibm-runtime/actions/workflows/ci.yml/badge.svg)](https://github.com/Qiskit/qiskit-ibm-runtime/actions/workflows/ci.yml)
[![](https://img.shields.io/github/release/Qiskit/qiskit-ibm-runtime.svg?style=popout-square)](https://github.com/Qiskit/qiskit-ibm-runtime/releases)
[![](https://img.shields.io/pypi/dm/qiskit-ibm-runtime.svg?style=popout-square)](https://pypi.org/project/qiskit-ibm-runtime/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage Status](https://coveralls.io/repos/github/Qiskit/qiskit-ibm-runtime/badge.svg?branch=main)](https://coveralls.io/github/Qiskit/qiskit-ibm-runtime?branch=main)


**Qiskit** is an open-source SDK for working with quantum computers at the level of extended quantum circuits, operators, and primitives.

**Qiskit IBM Runtime** is a new environment offered by IBM Quantum that streamlines quantum computations and provides optimal
implementations of the Qiskit primitives `sampler` and `estimator` for IBM Quantum hardware. It is designed to use additional classical compute resources to execute quantum circuits with more efficiency on quantum processors, by including near-time computations such as error suppression and error mitigation. Examples of error suppression include dynamical decoupling, noise-aware compilation, error mitigation including readout mitigation, zero-noise extrapolation (ZNE), and probabilistic error cancellation (PEC).

This module provides the interface to access the Qiskit Runtime service on IBM Quantum Platform.

## Installation

You can install this package using pip:

```bash
pip install qiskit-ibm-runtime
```

## Account setup

### Qiskit Runtime service on IBM Quantum Platform

| :warning: After the sunset of IBM Quantum Platform Classic the `ibm_quantum` channel option is no longer supported. The `ibm_cloud` and `ibm_quantum_platform` channels are now the only valid channels. See the [migration guide.](https://quantum.cloud.ibm.com/docs/migration-guides/classic-iqp-to-cloud-iqp) for more information.
|:---------------------------|


### Qiskit Runtime service on the new IBM Quantum Platform (IBM Cloud)

You will need your IBM Quantum Platform API token to authenticate with the runtime service:

1. Create an IBM Quantum Platform account or log in to your existing account by visiting the [IBM Quantum Platform login page].

2. Copy (and optionally regenerate) your API token from your
   [IBM Cloud account page].

The runtime service is now part of the IBM Quantum Services on IBM Cloud. To use this service, you'll
need to create an IBM Cloud account and a quantum service instance.
[This guide](https://quantum.cloud.ibm.com/docs/migration-guides/classic-iqp-to-cloud-iqp)
contains step-by-step instructions, including how to find your
IBM Cloud API key and Cloud Resource Name (CRN), which you will need for authentication.


### Save your account on disk

Once you have the account credentials, you can save them on disk, so you won't have to input
them each time. The credentials are saved in the `$HOME/.qiskit/qiskit-ibm.json` file, where `$HOME` is your home directory.

| :warning: Account credentials are saved in plain text, so only do so if you are using a trusted device. |
|:---------------------------|

 ```python
from qiskit_ibm_runtime import QiskitRuntimeService

# Save an IBM Cloud account.
QiskitRuntimeService.save_account(channel="ibm_cloud", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")

# 'ibm_quantum_platform' and 'ibm_cloud' point to the same channel so they can be used interchangeably
# In a future releases 'ibm_cloud' will be deprecated and removed in favor of 'ibm_quantum_platform'
QiskitRuntimeService.save_account(channel="ibm_quantum_platform", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")
```

Once the account is saved on disk, you can instantiate the service without any arguments:

```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
```

### Loading account from environment variables

Alternatively, the service can discover credentials from environment variables:
```bash
export QISKIT_IBM_TOKEN="MY_IBM_CLOUD_API_KEY"
export QISKIT_IBM_INSTANCE="MY_IBM_CLOUD_CRN"
export QISKIT_IBM_CHANNEL="ibm_quantum_platform"
```

Then instantiate the service without any arguments:
```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
```

### Enabling account for current Python session

As another alternative, you can also enable an account just for the current session by instantiating the
service with your credentials.

```python
from qiskit_ibm_runtime import QiskitRuntimeService

# For an IBM Cloud account.
ibm_cloud_service = QiskitRuntimeService(channel="ibm_quantum_platform", token="MY_IBM_CLOUD_API_KEY", instance="MY_IBM_CLOUD_CRN")
```

## Primitives

All quantum applications and algorithms level are fundamentally built using these steps:
1. Map classical inputs to a quantum problem
2. Translate problem for optimized quantum execution.
3. Execute the quantum circuits by using a primitive (Estimator or Sampler).
4. Post-process, return result in classical format.

**Primitives** are base-level functions that serve as building blocks for many quantum algorithms and applications.
Primitives accept vectorized inputs, where single circuits can be grouped with array-valued specifications. That is, one circuit can be executed for arrays of n parameter sets, n observables, or both (in the case of the estimator). Each group is called a Primitive Unified Bloc (PUB), and can be represented as a tuple.

The [primitive interfaces](https://quantum.cloud.ibm.com/docs/api/qiskit/primitives) are defined in Qiskit.

The IBM Runtime service offers these primitives with additional features, such as built-in error suppression and mitigation.

There are several different options you can specify when calling the primitives. See [Primitive options](https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/options) for more information.

### Primitive versions

Version 2 of the primitives is introduced by `qiskit-ibm-runtime` release 0.21.0. Version 1 of the primitives is no longer supported. Refer to [Migrate to the V2 primitives](https://quantum.cloud.ibm.com/docs/migration-guides/v2-primitives) on how to migrate to V2 primitives. The examples below all use V2 primitives.

### Sampler

This primitive takes a list of user circuits (including measurements) as input and returns the sampling output. The type of the output is defined by the program (typically bit-arrays), and the output data is separated by the classical register names.

To invoke the `Sampler` primitive

```python
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

service = QiskitRuntimeService()

# 1. A quantum circuit for preparing the quantum state (|00> + |11>)/rt{2}
bell = QuantumCircuit(2)
bell.h(0)
bell.cx(0, 1)
bell.measure_all()

# 2: Optimize problem for quantum execution.
backend = service.least_busy(operational=True, simulator=False)
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(bell)

# 3. Execute using the Sampler primitive
sampler = Sampler(mode=backend)
sampler.options.default_shots = 1024  # Options can be set using auto-complete.
job = sampler.run([isa_circuit])
print(f"Job ID is {job.job_id()}")
pub_result = job.result()[0]
print(f"Counts for the meas output register: {pub_result.data.meas.get_counts()}")
```

### Estimator

This primitive takes circuits and observables as input, to evaluate expectation values and standard error for a given parameter input. This Estimator allows users to efficiently calculate and interpret expectation values of quantum operators required for many algorithms.

To invoke the `Estimator` primitive:

```python
from qiskit_ibm_runtime import QiskitRuntimeService, EstimatorV2 as Estimator
from qiskit.quantum_info import SparsePauliOp
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
import numpy as np

service = QiskitRuntimeService()

# 1. A quantum circuit for preparing the quantum state (|000> + e^{itheta} |111>)/rt{2}
theta = Parameter('θ')
circuit = QuantumCircuit(3)
circuit.h(0) # generate superposition
circuit.p(theta, 0) # add quantum phase
circuit.cx(0, 1) # condition 1st qubit on 0th qubit
circuit.cx(0, 2) # condition 2nd qubit on 0th qubit

# The observable to be measured
M1 = SparsePauliOp.from_list([("XXY", 1), ("XYX", 1), ("YXX", 1), ("YYY", -1)])

# batch of theta parameters to be executed
points = 50
theta1 = []
for x in range(points):
    theta = [x*2.0*np.pi/50]
    theta1.append(theta)

# 2: Optimize problem for quantum execution.
backend = service.least_busy(operational=True, simulator=False)
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(circuit)
isa_observables = M1.apply_layout(isa_circuit.layout)

# 3. Execute using the Estimator primitive
estimator = Estimator(backend)
estimator.options.resilience_level = 1  # Options can be set using auto-complete.
job = estimator.run([(isa_circuit, isa_observables, theta1)])
print(f"Job ID is {job.job_id()}")
pub_result = job.result()[0]
print(f"Expectation values: {pub_result.data.evs}")
```

This code batches together 50 parameters to be executed in a single job. If a user wanted to find the `theta` that optimized the observable, they could plot and observe it occurs at `theta=np.pi/2`. For speed we recommend batching results together (note that depending on your access, there may be limits on the number of circuits, objects, and parameters that you can send).


## Session

In many algorithms and applications, an Estimator needs to be called iteratively without incurring queuing delays on each iteration. To solve this, the IBM Runtime service provides a **Session**. A session starts when the first job within the session is started, and subsequent jobs within the session are prioritized by the scheduler.

You can use the [`qiskit_ibm_runtime.Session`](https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/session.py) class to start a
session. Consider the same example above and try to find the optimal `theta`. The following example uses the [golden search method](https://en.wikipedia.org/wiki/Golden-section_search) to iteratively find the optimal theta that maximizes the observable.

To invoke the `Estimator` primitive within a session:

```python
from qiskit_ibm_runtime import QiskitRuntimeService, Session, EstimatorV2 as Estimator
from qiskit.quantum_info import SparsePauliOp
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
import numpy as np

service = QiskitRuntimeService()

# 1. A quantum circuit for preparing the quantum state (|000> + e^{itheta} |111>)/rt{2}
theta = Parameter('θ')
circuit = QuantumCircuit(3)
circuit.h(0) # generate superpostion
circuit.p(theta,0) # add quantum phase
circuit.cx(0, 1) # condition 1st qubit on 0th qubit
circuit.cx(0, 2) # condition 2nd qubit on 0th qubit

# The observable to be measured
M1 = SparsePauliOp.from_list([("XXY", 1), ("XYX", 1), ("YXX", 1), ("YYY", -1)])

gr = (np.sqrt(5) + 1) / 2 # golden ratio
thetaa = 0 # lower range of theta
thetab = 2*np.pi # upper range of theta
tol = 1e-1 # tol

# 2: Optimize problem for quantum execution.
backend = service.least_busy(operational=True, simulator=False)
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(circuit)
isa_observables = M1.apply_layout(isa_circuit.layout)

# 3. Execute iteratively using the Estimator primitive
with Session(backend=backend) as session:
    estimator = Estimator(mode=session)
    estimator.options.default_precision = 0.03  # Options can be set using auto-complete.
    #next test range
    thetac = thetab - (thetab - thetaa) / gr
    thetad = thetaa + (thetab - thetaa) / gr
    while abs(thetab - thetaa) > tol:
        print(f"max value of M1 is in the range theta = {[thetaa, thetab]}")
        job = estimator.run([(isa_circuit, isa_observables, [[thetac],[thetad]])])
        test = job.result()[0].data.evs
        if test[0] > test[1]:
            thetab = thetad
        else:
            thetaa = thetac
        thetac = thetab - (thetab - thetaa) / gr
        thetad = thetaa + (thetab - thetaa) / gr

    # Final job to evaluate Estimator at midpoint found using golden search method
    theta_mid = (thetab + thetaa) / 2
    job = estimator.run([(isa_circuit, isa_observables, theta_mid)])
    print(f"Session ID is {session.session_id}")
    print(f"Final Job ID is {job.job_id()}")
    print(f"Job result is {job.result()[0].data.evs} at theta = {theta_mid}")
```

This code returns `Job result is [4.] at theta = 1.575674623307102` using only nine iterations. This is a very powerful extension to the primitives. However, using too much code between iterative calls can lock the QPU and use excessive QPU time, which is expensive. We recommend only using sessions when needed. The Sampler can also be used within a session, but there are not any well-defined examples for this.

## Instances

Instances are virtual servers that manage your workload execution, including executing quantum programs and classical compute tasks (such as processing error mitigation). Instances are specified by their Cloud Resource Name (CRN).

You can see the instances you have access to on the [dashboard](https://quantum.cloud.ibm.com/) or by clicking the [Instances tab](https://quantum.cloud.ibm.com/instances) from the dashboard. Each instance is listed with its CRN identifier. You can include this identifier or the name of the instance when initializing the `QiskitRuntimeService` or saving your account. When an instance is passed in, only backends and jobs from that instance are available. Alternatively, if an instance is not included, then all backends and jobs across all instances in your account are available. In this case, when a backend is specified, an instance with the backend available will be used.

To view a list of your instances, you can also use the `instances()` method.

You can specify an instance when initializing the service or provider, or when picking a backend:

```python
# Optional: List all the instances you can access.
service = QiskitRuntimeService(channel='ibm_quantum_platform')
print(service.instances())

# Optional: Specify the instance at service level. This becomes the default unless overwritten.
service = QiskitRuntimeService(channel='ibm_quantum_platform', instance="IBM_CLOUD_INSTANCE_1")
backend1 = service.backend("ibmq_manila")

# Optional: Specify the instance at the backend level, which overwrites the service-level specification when this backend is used.
backend2 = service.backend("ibmq_manila", instance="IBM_CLOUD_INSTANCE_2")

sampler1 = Sampler(mode=backend1)    # IBM_CLOUD_INSTANCE_1
sampler2 = Sampler(mode=backend2)    # IBM_CLOUD_INSTANCE_2
```

If you do not specify an instance, then the code will select one in the following order:

1. If your account only has access to one instance, it is selected by default.
2. If your account has access to multiple instances, but only one can access the requested backend, the instance with access is selected.
3. In all other cases, the code selects the first instance that has access to the backend.

Priority of instance order can also be set with the ``region`` and ``plans_preference`` parameters. The official [release notes](https://docs.quantum.ibm.com/api/qiskit-ibm-runtime/release-notes#0400-2025-05-28) have examples on how these values can be used. 

## Access your IBM Quantum backends

A **backend** is a quantum device or simulator capable of running quantum circuits.

You can query for the backends you have access to. Attributes and methods of the returned instances
provide information, such as qubit counts, error rates, and statuses, of the backends.

```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()

# Display all backends you have access.
print(service.backends())

# Get a specific backend.
backend = service.backend('ibm_brisbane')

# Print backend coupling map.
print(backend.coupling_map)
```

## Next Steps

Now you're set up and ready to check out some of the [tutorials].

## Contribution guidelines

If you'd like to contribute to qiskit-ibm-runtime, please take a look at our
[contribution guidelines]. This project adheres to Qiskit's [code of conduct].
By participating, you are expected to uphold to this code.

We use [GitHub issues] for tracking requests and bugs. Please use our [slack]
for discussion and simple questions. To join our Slack community use the
invite link at [ibm.com/quantum/qiskit]. For questions that are more suited for a forum we
use the `Qiskit` tag in [Stack Exchange].

## Authors and Citation

Qiskit Runtime IBM Client is the work of [many people](https://github.com/Qiskit/qiskit-ibm-runtime/graphs/contributors) who contribute to the project at different levels.
If you use Qiskit, please cite as per the included [BibTeX file](https://github.com/Qiskit/qiskit/blob/main/CITATION.bib).

## License

[Apache License 2.0].


[New IBM Quantum Platform login page]:  https://quantum.cloud.ibm.com/
[IBM Cloud account page]: https://cloud.ibm.com/iam/apikeys
[contribution guidelines]: https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/CONTRIBUTING.md
[code of conduct]: https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/CODE_OF_CONDUCT.md
[GitHub issues]: https://github.com/Qiskit/qiskit-ibm-runtime/issues
[slack]: https://qiskit.slack.com
[ibm.com/quantum/qiskit]: https://www.ibm.com/quantum/qiskit
[Stack Exchange]: https://quantumcomputing.stackexchange.com/questions/tagged/qiskit
[many people]: https://github.com/Qiskit/qiskit-ibm-runtime/graphs/contributors
[BibTeX file]: https://github.com/Qiskit/qiskit/blob/master/Qiskit.bib
[Apache License 2.0]: https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/LICENSE.txt
[tutorials]: https://learning.quantum.ibm.com/catalog/tutorials
