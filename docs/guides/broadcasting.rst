Broadcast semantics of the executor
===================================

This guide explains how the executor handles array inputs and outputs using broadcasting semantics.
Understanding these concepts will help you efficiently sweep over parameter values, combine
multiple experimental configurations, and interpret the shape of returned data.

Quick start example
-------------------

Before diving into the details, here's a simple example that demonstrates the core idea. Suppose
you have a parametric circuit and want to run it with 5 different parameter configurations:

.. code-block:: python

    import numpy as np
    from qiskit.circuit import Parameter, QuantumCircuit
    from qiskit_ibm_runtime.quantum_program import QuantumProgram

    # A circuit with 3 parameters
    circuit = QuantumCircuit(3)
    circuit.rx(Parameter("a"), 0)
    circuit.rx(Parameter("b"), 1)
    circuit.rx(Parameter("c"), 2)
    circuit.measure_all()

    # 5 different parameter configurations (shape: 5 configurations × 3 parameters)
    parameter_values = np.linspace(0, np.pi, 15).reshape(5, 3)

    program = QuantumProgram(shots=1024)
    program.append(circuit, circuit_arguments=parameter_values)

    # Run and get results
    result = executor.run(program).result()

    # result is a list with one entry per program item
    # result[0] is a dict mapping classical register names to data arrays
    # Output bool arrays have shape (5, 1024, 3)
    #   5 = number of parameter configurations
    #   1024 = number of shots
    #   3 = bits in the classical register
    result[0]["meas"]

The executor automatically runs all 5 configurations and returns data organized by configuration,
with one result per classical register in each quantum program item. The rest of this guide explains
how this works in detail and how to build more complex sweeps, including samplomatic-based
randomization and inputs.

What is broadcasting?
---------------------

Broadcasting is a mechanism for combining arrays of different shapes in a systematic way. The
executor, like the sampler and estimator, uses NumPy-style broadcasting to determine how multiple
input arrays combine to define a grid of experimental configurations.

**The core rule:** Two shapes are compatible if, when aligned from the right, each pair of
dimensions is either equal or one of them is ``1``. A dimension of size ``1`` is "stretched"
to match the other.

.. list-table:: Broadcasting examples
   :header-rows: 1
   :widths: 30 30 40

   * - Shape A
     - Shape B
     - Broadcast result
   * - ``(5,)``
     - ``(5,)``
     - ``(5,)`` - element-wise pairing
   * - ``(3, 1)``
     - ``(4,)``
     - ``(3, 4)`` - 3×4 grid of combinations
   * - ``(2, 1, 5)``
     - ``(3, 1)``
     - ``(2, 3, 5)`` - all combinations across dimensions
   * - ``(3,)``
     - ``(4,)``
     - **Error** - incompatible shapes

When shapes broadcast together, the result contains all combinations along dimensions where one
input had size ``1``. This is how you create multi-dimensional parameter sweeps.

Intrinsic and extrinsic axes
----------------------------

Input arrays in the executor have two kinds of axes:

- **Intrinsic axes** (rightmost): Determined by the data type itself. For example, if your circuit
  has 3 parameters, then parameter values inherently need 3 numbers, giving an intrinsic shape
  of ``(3,)``.

- **Extrinsic axes** (leftmost): Your sweep dimensions. These define how many configurations you
  want to run.

.. list-table:: Intrinsic shapes of common inputs
   :header-rows: 1
   :widths: 40 30 30

   * - Input type
     - Intrinsic shape
     - Example full shape
   * - Parameter values (n parameters)
     - ``(n,)``
     - ``(5, 3)`` for 5 configurations, 3 parameters
   * - Scalar inputs (for example, noise scale)
     - ``()``
     - ``(4,)`` for 4 configurations
   * - Observables (if applicable)
     - varies
     - depends on observable type

**Key insight:** Broadcasting only applies to extrinsic axes. The intrinsic axes are always
preserved as - is.

Example: understanding extrinsic shapes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consider a circuit with 2 parameters that you want to sweep over a 4×3 grid of configurations,
varying both parameter values and a noise scale factor:

.. code-block:: python

    import numpy as np

    # Parameter values: 4 configurations along axis 0, intrinsic shape (2,)
    # Full shape: (4, 1, 2) - the "1" allows broadcasting with noise_scale
    parameter_values = np.array([
        [[0.1, 0.2]],
        [[0.3, 0.4]],
        [[0.5, 0.6]],
        [[0.7, 0.8]],
    ])  # shape (4, 1, 2)

    # Noise scale: 3 configurations, intrinsic shape () (scalar)
    # Full shape: (3,)
    noise_scale = np.array([0.8, 1.0, 1.2])  # shape (3,)

    # Extrinsic shapes: (4, 1) and (3,) → broadcast to (4, 3)
    # Result: 12 total configurations in a 4×3 grid

    program.append(
        template,
        samplex=samplex,
        samplex_arguments={
            "parameter_values": parameter_values,
            "noise_scale.mod_ref1": noise_scale,
        },
    )

Here's how the shapes break down:

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Input
     - Full shape
     - Extrinsic shape
     - Intrinsic shape
   * - ``parameter_values``
     - ``(4, 1, 2)``
     - ``(4, 1)``
     - ``(2,)``
   * - ``noise_scale``
     - ``(3,)``
     - ``(3,)``
     - ``()``
   * - **Broadcast**
     - -
     - ``(4, 3)``
     - -

Output array shapes
-------------------

Output arrays follow the same extrinsic/intrinsic pattern:

- **Extrinsic shape:** Matches the broadcast shape of all inputs
- **Intrinsic shape:** Determined by the output type

The most common output is bitstring data from measurements, which is 
formatted as an array of boolean values:

.. list-table:: Intrinsic shapes of common outputs
   :header-rows: 1
   :widths: 40 30 30

   * - Output type
     - Intrinsic shape
     - Description
   * - Classical register data
     - ``(num_shots, creg_size)``
     - Bitstring data from measurements
   * - Expectation values
     - ``()`` or ``(n_obs,)``
     - Scalar or per-observable

Example: predicting output shapes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you provide inputs with extrinsic shapes ``(4, 1)`` and ``(3,)``, the broadcast extrinsic
shape is ``(4, 3)``. For a circuit with 1024 shots and a 3-bit classical register:

.. code-block:: python

    # Input extrinsic shapes: (4, 1) and (3,) → (4, 3)
    # Output for classical register "meas":
    #   extrinsic: (4, 3)
    #   intrinsic: (1024, 3)  - shots × bits
    #   full shape: (4, 3, 1024, 3)

    result = executor.run(program).result()
    meas_data = result[0]["meas"]  # result[0] for first program item
    print(meas_data.shape)  # (4, 3, 1024, 3)

    # Access a specific configuration
    config_2_1 = meas_data[2, 1, :, :]  # shape (1024, 3)

.. note::

   Each configuration receives the full shot count specified in the quantum program. 
   Shots are **not** divided among configurations - if you request 1024 shots and have 
   10 configurations, each configuration runs 1024 shots (10,240 total shots executed).

Randomization and the ``shape`` parameter
-----------------------------------------

When using a samplex, each element of the extrinsic shape corresponds to an independent circuit
execution. The samplex will typically inject randomness (for example, twirling gates) into each
execution, so even without explicitly requesting multiple randomizations, each element naturally
receives its own random realization.

The ``shape`` parameter lets you augment the extrinsic shape for the item, effectively letting you
add axes that correspond specifically to randomizing the same configuration many times. It must be
broadcastable from the shape implicit in your ``samplex_arguments``. Axes where ``shape`` exceeds
the implicit shape enumerate additional independent randomizations.

No explicit randomization axes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you omit ``shape`` (or set it to match your input shapes), you get one execution per
input configuration. Each execution is still randomized by the samplex, but with only a
single random realization you don't benefit from averaging over multiple randomizations.

.. note::

   If you're used to enabling twirling with a simple flag like ``twirling=True``, note that
   the executor requires you to explicitly request multiple randomizations with the ``shape`` argument to
   allow your post-processing routines to get the benefits of averaging over multiple 
   randomizations. A single randomization (the default when ``shape`` is omitted) applies 
   random gates but typically offers no advantage over running the base circuit without 
   randomization.

The following example demonstrates the default behavior:

.. code-block:: python

    program.append(
        template,
        samplex=samplex,
        samplex_arguments={
            "parameter_values": np.random.rand(10, 3),  # extrinsic (10,)
        },
        # shape defaults to (10,) - one randomized execution per config
    )
    # Output shape for "meas": (10, num_shots, creg_size)

Single randomization axis
~~~~~~~~~~~~~~~~~~~~~~~~~

To run multiple randomizations per configuration, extend the shape with additional axes.
For example, 20 randomizations for each of 10 parameter configurations:

.. code-block:: python

    program.append(
        template,
        samplex=samplex,
        samplex_arguments={
            "parameter_values": np.random.rand(10, 3),  # extrinsic (10,)
        },
        shape=(20, 10),  # 20 randomizations × 10 configurations
    )
    # Output shape for "meas": (20, 10, num_shots, creg_size)

Multiple randomization axes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can organize randomizations into a multi-dimensional grid. This is useful for structured
analysis, for example, separating randomizations by type or grouping them for statistical processing:

.. code-block:: python

    program.append(
        template,
        samplex=samplex,
        samplex_arguments={
            "parameter_values": np.random.rand(10, 3),  # extrinsic (10,)
        },
        shape=(2, 14, 10),  # 2×14=28 randomizations per configuration, 10 configurations
    )
    # Output shape for "meas": (2, 14, 10, num_shots, creg_size)

Here, the input extrinsic shape ``(10,)`` broadcasts to the requested shape ``(2, 14, 10)``,
with axes 0 and 1 filled by independent randomizations.

How ``shape`` and input shapes interact
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``shape`` parameter must be broadcastable *from* your input extrinsic shapes. This means:

- Input shapes with size-1 dimensions can expand to match ``shape``
- Input shapes must align from the right with ``shape``
- Axes in ``shape`` that exceed the input dimensions enumerate randomizations

.. list-table:: Shape interaction examples
   :header-rows: 1
   :widths: 25 25 50

   * - Input extrinsic
     - ``shape``
     - Result
   * - ``(10,)``
     - ``(10,)``
     - 10 configurations, 1 randomization each
   * - ``(10,)``
     - ``(5, 10)``
     - 10 configurations, 5 randomizations each
   * - ``(10,)``
     - ``(2, 3, 10)``
     - 10 configurations, 2×3=6 randomizations each
   * - ``(4, 1)``
     - ``(4, 5)``
     - 4 configurations, 5 randomizations each
   * - ``(4, 3)``
     - ``(2, 4, 3)``
     - 4×3=12 configurations, 2 randomizations each
   * - ``(4, 3)``
     - ``(2, 1, 3)``
     - 4×3=12 configurations, 2 randomizations each (the ``1`` expands to ``4``)

Note that, as in the last example in the previous table, ``shape`` can contain size-1 dimensions
that expand to match input dimensions.


Indexing into results
~~~~~~~~~~~~~~~~~~~~~

With randomization axes, you can index into specific randomization/parameter combinations:

.. code-block:: python

    # Using shape=(2, 14, 10) with input extrinsic shape (10,)
    result = executor.run(program).result()
    meas_data = result[0]["meas"]  # shape (2, 14, 10, 1024, 3)

    # Get all shots for randomization (0, 7) and parameter config 3
    specific = meas_data[0, 7, 3, :, :]  # shape (1024, 3)

    # Average over all randomizations for parameter config 5 on bit 2
    averaged = meas_data[:, :, 5, :, 2].mean(axis=(0, 1))

Common patterns
---------------

Sweeping a single parameter
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To sweep one parameter while holding others fixed:

.. code-block:: python

    # Circuit has 3 parameters, sweep first one over 20 values
    sweep_values = np.linspace(0, 2*np.pi, 20)
    fixed_values = [0.5, 0.3]

    parameter_values = np.column_stack([
        sweep_values,
        np.full(20, fixed_values[0]),
        np.full(20, fixed_values[1]),
    ])  # shape (20, 3)

Creating a 2D grid sweep
~~~~~~~~~~~~~~~~~~~~~~~~

To create a grid over two parameters:

.. code-block:: python

    # Sweep param 0 over 10 values, param 1 over 8 values, param 2 fixed
    p0 = np.linspace(0, np.pi, 10)[:, np.newaxis, np.newaxis]  # (10, 1, 1)
    p1 = np.linspace(0, np.pi, 8)[np.newaxis, :, np.newaxis]   # (1, 8, 1)
    p2 = np.array([[[0.5]]])                                   # (1, 1, 1)

    parameter_values = np.broadcast_arrays(p0, p1, p2)
    parameter_values = np.stack(parameter_values, axis=-1).squeeze()  # (10, 8, 3)

    # Extrinsic shape: (10, 8), intrinsic shape: (3,)

Combining multiple inputs
~~~~~~~~~~~~~~~~~~~~~~~~~

When combining inputs with different intrinsic shapes, align extrinsic dimensions using
size-1 axes:

.. code-block:: python

    # 4 parameter configurations, 3 noise scales → 4×3 = 12 total configurations
    parameter_values = np.random.rand(4, 1, 2)  # extrinsic (4, 1), intrinsic (2,)
    noise_scale = np.array([0.8, 1.0, 1.2])     # extrinsic (3,), intrinsic ()

    # Broadcasted extrinsic shape: (4, 3)

