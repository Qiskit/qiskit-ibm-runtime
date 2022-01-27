#########################################
Qiskit IBM Runtime documentation
#########################################

Qiskit Runtime
==============

Qiskit Runtime is a new architecture offered by IBM Quantum that streamlines computations requiring
many iterations. These experiments will execute significantly faster within this improved hybrid quantum/classical process.

Using Qiskit Runtime, for example, a research team at IBM Quantum was able to achieve
`120x speedup <https://research.ibm.com/blog/120x-quantum-speedup>`_ in their lithium hydride simulation.

.. figure:: images/runtime_arch.png
    :align: center

Qiskit Runtime allows authorized users to upload their Qiskit quantum programs for themselves or
others to use. A Qiskit quantum program, also called a Qiskit runtime program, is a piece of Python code
that takes certain inputs, performs
quantum and maybe classical computation, and returns the processing results. The same or other
authorized users can then invoke these quantum programs by simply passing in the required input parameters.


Primitive programs
------------------

Primitive programs are predefined Qiskit Runtime programs that provide a simplified interface
for building and customizing applications. The
existing Qiskit interface to backends (currently ``backend.run()``) was originally designed in
a way that accepts a list of circuits and returns shot counts. Over time, it became clear that
users want other pieces of information too, whether that be memory to get pre-shot readouts to
more prominently observable expectation values coupled with all the possible ways to mitigate their error.

Eventually, you will be able to call primitives from a generic program definitions, and use the
primitive program interface that best suits your output needs to run circuits seamlessly and efficiently
on IBM quantum systems.

Qiskit IBM Runtime
==================

``qiskit-ibm-runtime`` provides the interface to interact with Qiskit Runtime. You can, for example,
use it to query and execute runtime programs:

In general, most users of the Qiskit Runtime execute programs that are predefined
and specified using a program name and a small number of input arguments, e.g.:

.. code-block:: python

    from qiskit_ibm_runtime import IBMRuntimeService

    # Authenticate with the service.
    service = IBMRuntimeService()

    # Print all available programs.
    service.pprint_programs()

    # Run the estimator program.
    program_inputs = {
      "circuit": ansatz,
      "observable": observable,
      "parameters": parameters
    }
    options = {"backend_name": "ibmq_bogota"}
    job = provider.runtime.run(program_id="estimator",
                               options=options,
                               inputs=program_inputs,
                              )

For additional information and usage examples see the :ref:`tutorials` page.

.. toctree::
    :hidden:

    API References <apidocs/ibm-runtime>
    Release Notes <release_notes>
    Maximum Execution Time <max_time.rst>
    Tutorials <tutorials.rst>


.. Hiding - Indices and tables
   :ref:`genindex`
   :ref:`modindex`
   :ref:`search`
