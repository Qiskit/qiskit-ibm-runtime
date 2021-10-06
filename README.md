# Qiskit Runtime

[![License](https://img.shields.io/github/license/Qiskit/qiskit-terra.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)

**Qiskit Runtime** is a new architecture offered by IBM Quantum that streamlines quantum computations.
It is designed to use classical compute resources to execute quantum circuits with more efficiency on quantum processors.

Using Qiskit Runtime, for example, a research team at IBM Quantum was able to achieve 120x speed 
up in their lithium hydride simulation. For more information, see the 
[IBM Research blog](https://research.ibm.com/blog/120x-quantum-speedup) 

Qiskit Runtime allows authorized users to upload their quantum programs for themselves or 
others to use. A quantum program, also called a Qiskit runtime program, is a piece of Python code that takes certain inputs, performs
quantum and classical computation, and returns the processing results. The same or other
authorized users can then invoke these quantum programs by simply passing in the required input parameters.

---
:rocket: Qiskit Runtime is now available on all IBM Quantum systems. If `ibm-q/open/main` is the 
only hub/group/project in your account, then you can only execute runtime programs on 
`ibmq_qasm_simulator`. If you have more than one hub/group/project, you can execute runtime programs
on any systems to which you have access and upload your custom programs.

---

## Installation

You need to install the required packages for the tutorials, which are documented in `requirements.txt`.
After that, you can download this repository and use Jupyter Notebook/Lab to explore the 
tutorials and learn how Qiskit Runtime works.

```bash
git clone https://github.com/Qiskit-Partners/qiskit-runtime.git
cd qiskit-runtime
pip install -r requirements.txt

cd tutorials
jupyter notebook .
```

## Executing a Qiskit Runtime program

### Configuring your IBM Quantum credentials

Before you can start using Qiskit Runtime, make sure you have an [IBM Quantum](https://quantum-computing.ibm.com)
account. If this is 
your first time using IBM Quantum or Qiskit, please refer to the instruction in the 
[`qiskit-ibmq-provider`](https://github.com/Qiskit/qiskit-ibmq-provider#configure-your-ibm-quantum-experience-credentials)
repository to configure your IBM Quantum credentials.

### Finding available programs

To list all available programs:

```python

from qiskit import IBMQ

IBMQ.load_account()
provider = IBMQ.get_provider(hub='MY_HUB', group='MY_GROUP', project='MY_PROJECT')
provider.runtime.pprint_programs()
```

`pprint_programs()` prints the metadata of all programs visible to you. A program's metadata 
consists of its ID, name, description, input parameters, return values, interim results, and 
other information that helps you to know more about the program.

If you know the ID of the program you're looking for, you can also print out the metadata of just 
that one program:

```python
print(provider.runtime.program('sample-program'))
```

The output of the code above would be:

```
sample-program:
  Name: sample-program
  Description: A sample runtime program.
  Version: 1
  Creation date: 2021-05-04T01:38:21Z
  Max execution time: 300
  Parameters:
    - iterations:
      Description: Number of iterations to run. Each iteration generates and runs a random circuit.
      Type: int
      Required: True
  Interim results:
    - iteration:
      Description: Iteration number.
      Type: int
    - counts:
      Description: Histogram data of the circuit result.
      Type: dict
  Returns:
    - -:
      Description: A string that says 'All done!'.
      Type: string
```

`sample-program`, as the name suggests, is a sample program used for demonstration. 
It takes only 1 input parameter `iterations`, which indicates how many iterations to run. 
For each iteration it generates and runs a random 5-qubit circuit and returns the counts as well 
as the iteration number as the interim results. When the program finishes, it returns the sentence 
`All done!`. This program has a maximum execution time of 300 seconds, after which the execution will
be forcibly terminated.  

### Executing the `sample-program` program

Because `sample-program` provides interim results, which are results available to you while the program is
still running, we want to first define a callback function that would handle these interim results:

```python
def interim_result_callback(job_id, interim_result):
    print(f"interim result: {interim_result}")
``` 

When an interim result is available, this callback function will be invoked and the result data passed to it.
Not all programs provide interim results, and you don't have to provide a callback even if the program you're 
executing does provide them.

To run the `sample-program` program:

```python
program_inputs = {
    'iterations': 3
}
options = {'backend_name': 'ibmq_montreal'}
job = provider.runtime.run(program_id="sample-program",
                           options=options,
                           inputs=program_inputs,
                           callback=interim_result_callback
                          )
print(f"job ID: {job.job_id()}")
result = job.result()
```

### Deleting your job

While not strictly necessary, deleting unwanted jobs can help with performance when you want to query
for old jobs. To delete a job:

```python
provider.runtime.delete_job('JOB_ID')
```

## Limitations

### API

Qiskit Runtime is still in beta mode, and heavy modifications to both functionality and API 
are likely to occur. Some of the changes might not be backward compatible and would require updating
your Qiskit version.

## Next Steps

This README only provides a quick overview of Qiskit Runtime. Check out the 
[tutorials](https://github.com/Qiskit-Partners/qiskit-runtime/tree/main/tutorials).
The Qiskit user interface for accessing Qiskit Runtime is provided by `qiskit-ibmq-provider`, so you
might want to also check out its [runtime API documentation](https://qiskit.org/documentation/apidoc/ibmq_runtime.html).

## License

[Apache License 2.0](LICENSE.txt)
