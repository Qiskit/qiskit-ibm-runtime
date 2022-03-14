# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
==========================================
Qiskit Runtime (:mod:`qiskit_ibm_runtime`)
==========================================

.. currentmodule:: qiskit_ibm_runtime

Modules related to Qiskit Runtime IBM Quantum Client.

Qiskit Runtime is a new architecture that
streamlines computations requiring many iterations. These experiments will
execute significantly faster within its improved hybrid quantum/classical process.

Qiskit Runtime IBM Quantum Client allows authorized users to upload their Qiskit quantum programs.
A Qiskit quantum program, also called a runtime program, is a piece of Python
code and its metadata that takes certain inputs, performs
quantum and maybe classical processing, and returns the results. The same or other
authorized users can invoke these quantum programs by simply passing in parameters.

Account initialization
----------------------

You need to initialize your account before you can start using the Qiskit Runtime service.
This is done by initializing an :class:`IBMRuntimeService` instance with your
account credentials. If you don't want to pass in the credentials each time, you
can use the :meth:`IBMRuntimeService.save_account` method to save the credentials
on disk.

Qiskit Runtime is available on both IBM Cloud and IBM Quantum, and you can specify
``auth="cloud"`` for IBM Cloud and ``auth="legacy"`` for IBM Quantum. The default
is IBM Cloud.

Listing runtime programs
------------------------

To list all available runtime programs::

    from qiskit_ibm_runtime import IBMRuntimeService

    service = IBMRuntimeService()

    # List all available programs.
    service.pprint_programs()

    # Get a single program.
    program = service.program('sampler')

    # Print program metadata.
    print(program)

The example above prints the program metadata of all
available runtime programs and of just the ``sampler`` program. A program
metadata consists of the program's ID, name, description, input parameters,
return values, interim results, and other information that helps you to know
more about the program.

Invoking a runtime program
--------------------------

You can use the :meth:`IBMRuntimeService.run` method to invoke a runtime program.
For example::

    from qiskit import QuantumCircuit
    from qiskit_ibm_runtime import IBMRuntimeService

    service = IBMRuntimeService()
    backend = "ibmq_qasm_simulator"

    # Create a circuit.
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    # Set the "sampler" program parameters
    params = service.program(program_id="sampler").parameters()
    params.circuits = qc

    # Configure backend options
    options = {'backend_name': backend}

    # Execute the circuit using the "sampler" program.
    job = service.run(program_id="sampler",
                      options=options,
                      inputs=params)

    # Get runtime job result.
    result = job.result()

The example above invokes the ``sampler`` program.

Runtime Jobs
------------

When you use the :meth:`IBMRuntimeService.run` method to invoke a runtime
program, a
:class:`RuntimeJob` instance is returned. This class has all the basic job
methods, such as :meth:`RuntimeJob.status`, :meth:`RuntimeJob.result`, and
:meth:`RuntimeJob.cancel`.

Interim and final results
-------------------------

Some runtime programs provide interim results that inform you about program
progress. You can choose to stream the interim results and final result when you run the
program by passing in the ``callback`` parameter, or at a later time using
the :meth:`RuntimeJob.stream_results` method. For example::

    from qiskit import QuantumCircuit
    from qiskit_ibm_runtime import IBMRuntimeService

    service = IBMRuntimeService()
    backend = "ibmq_qasm_simulator"

    def result_callback(job_id, result):
        print(result)

    # Stream results as soon as the job starts running.
    job = service.run(program_id="sampler",
                      options=options,
                      inputs=program_inputs,
                      callback=result_callback)

Backend data
------------

:class:`IBMRuntimeService` also has methods, such as :meth:`backend`,
:meth:`backends`, and :meth:`least_busy`, that allows you to query for a target
backend to use. These methods return one or more :class:`IBMBackend` instances
that contains methods and attributes describing the backend.


Uploading a program
-------------------

Each runtime program has both ``data`` and ``metadata``. Program data is
the Python code to be executed. Program metadata provides usage information,
such as program description, its inputs and outputs, and backend requirements.
A detailed program metadata helps the consumers of the program to know what is
needed to run the program.

Each program data needs to have a ``main(backend, user_messenger, **kwargs)``
method, which serves as the entry point to the program. The ``backend`` parameter
is a :class:`ProgramBackend` instance whose :meth:`ProgramBackend.run` method
can be used to submit circuits. The ``user_messenger`` is a :class:`UserMessenger`
instance whose :meth:`UserMessenger.publish` method can be used to publish interim and
final results.
See `qiskit_ibm_runtime/program/program_template.py` for a program data
template file.

Each program metadata must include at least the program name, description, and
maximum execution time. You can find description of each metadata field in
the :meth:`IBMRuntimeService.upload_program` method. Instead of passing in
the metadata fields individually, you can pass in a JSON file or a dictionary
to :meth:`IBMRuntimeService.upload_program` via the ``metadata`` parameter.
`qiskit_ibm_runtime/program/program_metadata_sample.json`
is a sample file of program metadata.

You can use the :meth:`IBMRuntimeService.upload_program` to upload a program.
For example::

    from qiskit_ibm_runtime import IBMRuntimeService

    service = IBMRuntimeService()
    program_id = service.upload_program(
                    data="my_vqe.py",
                    metadata="my_vqe_metadata.json"
                )

In the example above, the file ``my_vqe.py`` contains the program data, and
``my_vqe_metadata.json`` contains the program metadata.

Method :meth:`IBMRuntimeService.delete_program` allows you to delete a
program.

Files related to writing a runtime program are in the
``qiskit_ibm_runtime/program`` directory.


Logging
-------

`qiskit-ibm-runtime` uses the ``qiskit_ibm_runtime`` logger.

Two environment variables can be used to control the logging:

    * ``QISKIT_IBM_RUNTIME_LOG_LEVEL``: Specifies the log level to use.
      If an invalid level is set, the log level defaults to ``WARNING``.
      The valid log levels are ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``
      (case-insensitive). If the environment variable is not set, then the parent logger's level
      is used, which also defaults to ``WARNING``.
    * ``QISKIT_IBM_RUNTIME_LOG_FILE``: Specifies the name of the log file to use. If specified,
      messages will be logged to the file only. Otherwise messages will be logged to the standard
      error (usually the screen).

For more advanced use, you can modify the logger itself. For example, to manually set the level
to ``WARNING``::

    import logging
    logging.getLogger('qiskit_ibm_runtime').setLevel(logging.WARNING)

Classes
==========================
.. autosummary::
   :toctree: ../stubs/

   IBMRuntimeService
   IBMEstimator
   IBMSampler
   IBMBackend
   RuntimeJob
   RuntimeProgram
   ParameterNamespace
   RuntimeOptions
   RuntimeEncoder
   RuntimeDecoder
"""

import logging

from .ibm_runtime_service import IBMRuntimeService
from .ibm_backend import IBMBackend
from .runtime_job import RuntimeJob
from .runtime_program import RuntimeProgram, ParameterNamespace
from .runtime_options import RuntimeOptions
from .utils.json import RuntimeEncoder, RuntimeDecoder

from .exceptions import *
from .utils.utils import setup_logger
from .version import __version__

from .ibm_estimator import IBMEstimator
from .ibm_sampler import IBMSampler

# TODO remove when terra code is released
from .qiskit.primitives import (
    BaseEstimator,
    EstimatorResult,
    BaseSampler,
    SamplerResult,
)

# Setup the logger for the IBM Quantum Provider package.
logger = logging.getLogger(__name__)
setup_logger(logger)

# Constants used by the IBM Quantum logger.
QISKIT_IBM_RUNTIME_LOGGER_NAME = "qiskit_ibm_runtime"
"""The name of the IBM Quantum logger."""
QISKIT_IBM_RUNTIME_LOG_LEVEL = "QISKIT_IBM_RUNTIME_LOG_LEVEL"
"""The environment variable name that is used to set the level for the IBM Quantum logger."""
QISKIT_IBM_RUNTIME_LOG_FILE = "QISKIT_IBM_RUNTIME_LOG_FILE"
"""The environment variable name that is used to set the file for the IBM Quantum logger."""
