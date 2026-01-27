The Executor: A quick-start guide
================================= 

This guide provides a basic overview of the :class:`~.Executor`, a runtime program that allows
executing :class:`~.QuantumProgram`\s on IBM backends. At the end of this guide, you will
know how to:

* Initialize a :class:`~.QuantumProgram` with your workload.
* Run :class:`~.QuantumProgram`\s on IBM backends using the :class:`~.Executor`.
* Interpret the outputs of the :class:`~.Executor`.

In the remainder of the guide, we consider a circuit that generates a three-qubit GHZ state, rotates
the qubits around the Pauli-Z axis, and measures the qubits in the computational basis. We show how
to add this circuit to a :class:`~.QuantumProgram`, optionally randomizing its content with twirling
gates, and how to execute the program via the :class:`~.Executor`.

.. code-block:: python

    from qiskit.circuit import Parameter, QuantumCircuit

    # A circuit of the type considered in this guide
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.h(1)
    circuit.cz(0, 1)
    circuit.h(1)
    circuit.h(2)
    circuit.cz(1, 2)
    circuit.h(2)
    circuit.rz(Parameter("theta"), 0)
    circuit.rz(Parameter("phi"), 1)
    circuit.rz(Parameter("lam"), 2)
    circuit.measure_all()

Let us choose a backend to run our executor jobs with:

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False)

We can now begin by taking a look at the inputs to the :class:`~.Executor`, the :class:`~.QuantumProgram`\s.

The inputs to the Executor: Quantum Programs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A :class:`~.QuantumProgram` is an iterable of
:class:`~.qiskit_ibm_runtime.quantum_program.QuantumProgramItem`\s. Each of these items represents a
different task for the :class:`~.Executor` to perform. Typically, each item owns:

* a :class:`~qiskit.circuit.QuantumCircuit` with static, non-parametrized gates;
* or a parametrized :class:`~qiskit.circuit.QuantumCircuit`, together with an array of parameter values;
* or a parametrized :class:`~qiskit.circuit.QuantumCircuit`, together with a
  :class:`~samplomatic.samplex.Samplex` to generate randomize arrays of parameter values.

Let us take a closer look at each of these items and how to add them to a :class:`~.QuantumProgram`\.

In the cell below, we initialize a :class:`~.QuantumProgram` and specify that we wish to perform ``1024``
shots for every configuration of each item in the program. Next, we append a version of our target circuit with set parameters,
transpiled according to the backend's ISA.

.. code-block:: python

    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime.quantum_program import QuantumProgram

    # Initialize an empty program
    program = QuantumProgram(shots=1024)

    # Initialize circuit to generate and measure GHZ state
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.h(1)
    circuit.cz(0, 1)
    circuit.h(1)
    circuit.h(2)
    circuit.cz(1, 2)
    circuit.h(2)
    circuit.rz(0.1, 0)
    circuit.rz(0.2, 1)
    circuit.rz(0.3, 2)
    circuit.measure_all()

    # Transpile the circuit
    preset_pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
    isa_circuit = preset_pass_manager.run(circuit)

    # Append the circuit to the program
    program.append_circuit_item(isa_circuit)

We proceed to append a second item that contains a parametrized :class:`~qiskit.circuit.QuantumCircuit`
and an array containing ``10`` sets of parameter values. This amounts to a circuit task requiring a total
of ``10240`` shots (namely ``1024`` per set of parameter values).

.. code-block:: python

    from qiskit.circuit import Parameter
    import numpy as np

    # Initialize circuit to generate a GHZ state, rotate it around the Pauli-Z
    # axis, and measure it
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.h(1)
    circuit.cz(0, 1)
    circuit.h(1)
    circuit.h(2)
    circuit.cz(1, 2)
    circuit.h(2)
    circuit.rz(Parameter("theta"), 0)
    circuit.rz(Parameter("phi"), 1)
    circuit.rz(Parameter("lam"), 2)
    circuit.measure_all()

    # Transpile the circuit
    isa_circuit = preset_pass_manager.run(circuit)

    # Append the circuit and the parameter value to the program
    program.append_circuit_item(
        isa_circuit,
        circuit_arguments=np.random.rand(10, 3),  # 10 sets of parameter values
    )

Finally, in the next cell we append a parametrized :class:`~qiskit.circuit.QuantumCircuit` and a
:class:`~samplomatic.samplex.Samplex`, which is responsible for generating randomized sets of
parameters for the given circuit. As part of the :class:`~samplomatic.samplex.Samplex` arguments,
we provide ``10`` sets of parameters for the parametric gates in the original circuit.
Additionally, we use the ``shape`` request argument to request an extension of the implicit shape
defined by the :class:`~samplomatic.samplex.Samplex` arguments. In particular, by setting ``shape``
to ``(2, 14, 10)`` we request to randomize each of the ``10`` sets of parameters ``28`` times, and
to arrange the randomized parameter sets in an array of be arranged in an array of shape
``(2, 14, 10)``.

    We refer the reader to :mod:`~samplomatic` and its documentation for more details on the
    :class:`~samplomatic.samplex.Samplex` and its arguments.

.. code-block:: python

    from samplomatic import build
    from samplomatic.transpiler import generate_boxing_pass_manager

    # Initialize circuit to generate a GHZ state, rotate it around the Pauli-Z
    # axis, and measure it
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.h(1)
    circuit.cz(0, 1)
    circuit.h(1)
    circuit.h(2)
    circuit.cz(1, 2)
    circuit.h(2)
    circuit.rz(Parameter("theta"), 0)
    circuit.rz(Parameter("phi"), 1)
    circuit.rz(Parameter("lam"), 2)
    circuit.measure_all()

    # Transpile the circuit, additionally grouping gates and measurements into annotated boxes
    preset_pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
    preset_pass_manager.post_scheduling = generate_boxing_pass_manager(
        enable_gates=True,
        enable_measures=True,
    )
    boxed_circuit = preset_pass_manager.run(circuit)

    # Build the template and the samplex
    template, samplex = build(boxed_circuit)

    # Append the template and samplex as a samplex item
    program.append_samplex_item(
        template,
        samplex=samplex,
        samplex_arguments={  
            # the arguments required by the samplex.sample method
            "parameter_values": np.random.rand(10, 3),
        },
        shape=(2, 14, 10),
    )

Now that we have populated our :class:`~.QuantumProgram`, we can proceed with execution.

Running an Executor job
~~~~~~~~~~~~~~~~~~~~~~~

In the cell below we initialize an :class:`~.Executor` and leave the default options:

    .. code-block:: python

        from qiskit_ibm_runtime import Executor

        executor = Executor(backend)

Next, we use the :meth:`~.Executor.run` method to submit the job.

    .. code-block:: python
        
        job = executor.run(program)

        # Retrieve the result
        result = job.result()

Here, ``result`` is of type :class:`~.qiskit_ibm_runtime.quantum_program.QuantumProgramResult`.
We now take a closer look at this result object.

The outputs of the Executor
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~.qiskit_ibm_runtime.quantum_program.QuantumProgramResult` is an iterable. It contains one
item per circuit task, and the items are in the same order as the items in the program. Every one of
these items is a dictionary from strings to an ``np.ndarray``. with elements of type ``bool``. Let us
take a look at the three items in ``result`` to understand the meaning of their key-value pairs.

The first item in ``result`` contains the results of running the first task in the program, namely
the circuit with static gates. It contains a single key, ``'meas'``, corresponding to the name of the
classical register in the input circuit. The ``'meas'`` key is mapped to the results collected for this
classical registers, stored in an ``np.ndarray`` of shape ``(1024, 3)``. The first axis
is over shots, the second is over bits in the classical register.    

    .. code-block:: python
        
        # Access the results of the classical register of task #0
        result_0 = result[0]["meas"]
        print(f"Result shape: {result_0.shape}")

The second item contains the results of running the second task in the program, namely
the circuit with parametrized gates. Again, it contains a single key, ``'meas'``, mapped to a
``np.ndarray`` of shape ``(1024, 10, 3)``. The central axis is over parameter sets, while the first
and last are again over shots and bits respectively.  

    .. code-block:: python
        
        # Access the results of the classical register of task #1
        result_1 = result[1]["meas"]
        print(f"Result shape: {result_1.shape}")

Finally, the third item in ``result`` contains the results of running the third task in the program. This item
contains multiple key. In more detail, in addition to the ``'meas'`` key (mapped to the array of results for
that classical register), it contains ``'measurement_flips.meas'``, namely the bit-flip corrections to undo
the measurement twirling for the ``'meas'`` register.

    .. code-block:: python
        
        # Access the results of the classical register of task #2
        result_2 = result[2]["meas"]
        print(f"Result shape: {result_2.shape}")
        
        # Access the bit-flip corrections
        flips_2 = result[2]["measurement_flips.meas"]
        print(f"Result shape: {result_0.shape}")

        # Undo the bit flips via classical XOR
        unflipped_result_2 = result_2 ^ flips_2