##########################
Qiskit runtime (|version|)
##########################

.. important:: 

    The Qiskit runtime is currently in beta mode, and is in limited release.


The Qiskit runtime is a new execution model / architecture that markedly reduces
IO overhead when submitting applications and algorithms to quantum processors that
require many iterations of circuit executions and classical processing.  Programs of this
category are common, and span a wide variety of applications spaces including chemistry,
machine learning, and optimization.  

In general, most users of the Qiskit runtime execute programs that are predefined
and specified using a program name and a small number of input arguments, e.g.:

.. code-block:: python

    runtime_inputs = {'circuits': circuit,
                      'optimization_level': 3
                     }
    options = {'backend_name': backend.name()}
    job = provider.runtime.run(program_id="circuit-runner",
                               options=options,
                               inputs=runtime_inputs,
                              )
 
It is also possible to define custom programs and upload them to the Cloud infrastructure,
although access to this functionality is limited at present.

For additional information and usage examples see the :ref:`tutorials` page.


.. toctree::
    :hidden:

    self


.. toctree::
    :maxdepth: 1
    :caption: Program examples
    :hidden:
  
    Circuit runner <example_scripts/circuit_runner>
    VQE <example_scripts/vqe>

.. toctree::
    :maxdepth: 1
    :caption: API documentation
    :hidden:
  
    Circuit runner <apidocs/circuit_runner>