The Executor: A quick-start guide
================================= 

This guide provides a basic overview of the :class:`~.Executor`, a runtime program that allows
executing :class:`~.QuantumProgram`\s on IBM backend. At the end of this guide, you will
know how to:

* Initialize a :class:`~.QuantumProgram` to specify one or more circuit tasks.
* Run :class:`~.QuantumProgram`\s on IBM backends using the :class:`~.Executor`.
* Interpret the outputs of the :class:`~.Executor`.

In the reminder of the guide, we consider a circuit that generates a three-qubit GHZ state, rotates
the qubits around the Pauli-X axis, and measures the qubits in the computational basis. We show how
to add this circuit to a :class:`~.QuantumProgram`, optionally randomizing its content with twirling
gates, and how to execute the program via the :class:`~.Executor`.

.. code-block:: python

    from qiskit.circuit import QuantumCircuit, Parameter

    # A circuit of the type considered in this guide
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.rx(Parameter("theta"), 0)
    circuit.rx(Parameter("phi"), 1)
    circuit.rx(Parameter("lam"), 2)
    circuit.measure_all()

Let us choose a backend to run our executor jobs with:

.. code-block:: python

    from qiskit_ibm_runtime import QiskitRuntimeService, Executor

    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False)

We can now begin by taking a look at the inputs to the :class:`~.Executor`, the :class:`~.QuantumProgram`\s.

The inputs to the Executor: Quantum Programs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A :class:`~.QuantumProgram` is an iterable of
:class:`~.qiskit_ibm_runtime.quantum_program.QuantumProgramItem`\s. Each of these items represents a
different circuit task for the :class:`~.Executor` to perform. Typically, they own:

* a :class:`~qiskit.circuit.QuantumCircuit` with non-parametrized gates;
* or a parametrized :class:`~qiskit.circuit.QuantumCircuit`, together with an array of parameter values;
* or a parametrized :class:`~qiskit.circuit.QuantumCircuit`, together with a
  :class:`~samplomatic.samplex.Samplex` to generate randomize arrays of parameter values.

Let us take a closer look at each of these items and how to add them to a :class:`~.QuantumProgram`\.

In the cell below, we initialize a :class:`~.QuantumProgram` and specify that we wish to perform ``1024``
shots per item in the program. Next, we append a version of our target circuit with set parameters,
transpiled according to the backend's ISA.

.. code-block:: python
    from qiskit.circuit import QuantumCircuit
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime.quantum_program import QuantumProgram

    # Initialize an empty program
    program = QuantumProgram(shots=1024)

    # Initialize circuit to generate and measure GHZ state
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.rx(0.1, 0)
    circuit.rx(0.2, 1)
    circuit.rx(0.3, 2)
    circuit.measure_all()

    # Transpile the circuit
    preset_pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
    isa_circuit = preset_pass_manager.run(circuit)

    # Append the circuit to the program
    program.append(isa_circuit)

We the proceed to append a second item that contains a parametrized :class:`~qiskit.circuit.QuantumCircuit`
and an array containing ``10`` sets of parameter values. This amounts to a circuit task requiring a total
of ``10240`` shots (namely ``1024`` per set of parameter values).

.. code-block:: python

    from qiskit.circuit import Parameter
    import numpy as np

    # Initialize circuit to generate a GHZ state, rotate it around the Pauli-X
    # axis, and measure it
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.rx(Parameter("theta"), 0)
    circuit.rx(Parameter("phi"), 1)
    circuit.rx(Parameter("lam"), 2)
    circuit.measure_all()

    # Transpile the circuit
    isa_circuit = preset_pass_manager.run(circuit)

    # Append the circuit and the parameter value to the program
    program.append(
        isa_circuit,
        circuit_arguments=np.random.rand(10, 3),  # 10 sets of parameter values
    )

Finally, in the next cell we append a parametrized :class:`~qiskit.circuit.QuantumCircuit` and a
:class:`~samplomatic.samplex.Samplex`, which is responsible for generating randomized sets of
parameters for the given circuit. As part of the samplex arguments, we provide ``10`` sets of
parameters for the parametric gates in the original circuit.  This amounts to a circuit task
requiring a total of ``10240`` shots (namely ``1024`` per set of parameter values).

    We refer the reader to :mod:`~samplomatic` and its documentation for more details on the
    :class:`~samplomatic.samplex.Samplex` and its arguments.

.. code-block:: python

    from samplomatic import build
    from samplomatic.transpiler import generate_boxing_pass_manager

    # Initialize circuit to generate a GHZ state, rotate it around the Pauli-X
    # axis, and measure it
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.rx(Parameter("theta"), 0)
    circuit.rx(Parameter("phi"), 1)
    circuit.rx(Parameter("lam"), 2)
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
    program.append(
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

In the cell below we initialize an :class:`~.Executor` and set some of its options to custom
values.

    .. code-block:: python

        from qiskit_ibm_runtime import Executor

        # Initialize the executor and set its options
        executor = Executor(backend)
        executor.options.execution.init_qubits = True

Next, we use the :meth:`~.Executor.run` method to submit the job.

    .. code-block:: python
        
        job = executor.run(program)

        # Retrieve the result
        result = job.result()