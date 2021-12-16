# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
==============================================
Runtime (:mod:`qiskit_ibm_runtime`)
==============================================

.. currentmodule:: qiskit_ibm_runtime

Modules related to Qiskit IBM Runtime Service.

.. caution::

  This package is currently provided in beta form and heavy modifications to
  both functionality and API are likely to occur. Backward compatibility is not
  always guaranteed.

Qiskit Runtime is a new architecture offered by IBM Quantum that
streamlines computations requiring many iterations. These experiments will
execute significantly faster within its improved hybrid quantum/classical process.

The Qiskit Runtime Service allows authorized users to upload their Qiskit quantum programs.
A Qiskit quantum program, also called a runtime program, is a piece of Python
code and its metadata that takes certain inputs, performs
quantum and maybe classical processing, and returns the results. The same or other
authorized users can invoke these quantum programs by simply passing in parameters.

`Qiskit-Partners/qiskit-runtime <https://github.com/Qiskit-Partners/qiskit-runtime>`_
contains detailed tutorials on how to use Qiskit Runtime.


Listing runtime programs
------------------------

To list all available runtime programs::

    from qiskit_ibm_runtime import IBMRuntimeService

    service = IBMRuntimeService()

    # List all available programs.
    service.pprint_programs()

    # Get a single program.
    program = service.program('circuit-runner')

    # Print program metadata.
    print(program)

In the example above, ``service.runtime`` points to the runtime service class
:class:`IBMRuntimeService`, which is the main entry
point for using this service. The example prints the program metadata of all
available runtime programs and of just the ``circuit-runner`` program. A program
metadata consists of the program's ID, name, description, input parameters,
return values, interim results, and other information that helps you to know
more about the program.

Invoking a runtime program
--------------------------

You can use the :meth:`IBMRuntimeService.run` method to invoke a runtime program.
For example::

    from qiskit import QuantumCircuit
    from qiskit_ibm_runtime import IBMRuntimeService, RunnerResult

    service = IBMRuntimeService()
    backend = service.ibmq_qasm_simulator

    # Create a circuit.
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    # Set the "circuit-runner" program parameters
    params = service.program(program_id="circuit-runner").parameters()
    params.circuits = qc
    params.measurement_error_mitigation = True

    # Configure backend options
    options = {'backend_name': backend.name()}

    # Execute the circuit using the "circuit-runner" program.
    job = service.run(program_id="circuit-runner",
                      options=options,
                      inputs=params)

    # Get runtime job result.
    result = job.result(decoder=RunnerResult)

The example above invokes the ``circuit-runner`` program,
which compiles, executes, and optionally applies measurement error mitigation to
the circuit result.

Runtime Jobs
------------

When you use the :meth:`IBMRuntimeService.run` method to invoke a runtime
program, a
:class:`RuntimeJob` instance is returned. This class has all the basic job
methods, such as :meth:`RuntimeJob.status`, :meth:`RuntimeJob.result`, and
:meth:`RuntimeJob.cancel`. Note that it does not have the same methods as regular
circuit jobs, which are instances of :class:`~qiskit_ibm_runtime.job.IBMJob`.

Interim results
---------------

Some runtime programs provide interim results that inform you about program
progress. You can choose to stream the interim results when you run the
program by passing in the ``callback`` parameter, or at a later time using
the :meth:`RuntimeJob.stream_results` method. For example::

    from qiskit import QuantumCircuit
    from qiskit_ibm_runtime import IBMRuntimeService

    service = IBMRuntimeService()
    backend = service.ibmq_qasm_simulator

    def interim_result_callback(job_id, interim_result):
        print(interim_result)

    # Stream interim results as soon as the job starts running.
    job = service.run(program_id="circuit-runner",
                      options=options,
                      inputs=program_inputs,
                      callback=interim_result_callback)

Uploading a program
-------------------

.. note::

  Only authorized accounts can upload programs. Having access to the
  runtime service doesn't imply access to upload programs.

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
See `qiskit_ibm_runtime/runtime/program/program_template.py` for a program data
template file.

Each program metadata must include at least the program name, description, and
maximum execution time. You can find description of each metadata field in
the :meth:`IBMRuntimeService.upload_program` method. Instead of passing in
the metadata fields individually, you can pass in a JSON file or a dictionary
to :meth:`IBMRuntimeService.upload_program` via the ``metadata`` parameter.
`qiskit_ibm_runtime/runtime/program/program_metadata_sample.json`
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
``qiskit_ibm_runtime/runtime/program`` directory.


Classes
==========================
.. autosummary::
   :toctree: ../stubs/

   IBMRuntimeService
   RuntimeJob
   RuntimeProgram
   UserMessenger
   ProgramBackend
   ResultDecoder
   RuntimeEncoder
   RuntimeDecoder
   ParameterNamespace
"""
# """
# ===================================================
# IBM Quantum Provider (:mod:`qiskit_ibm_runtime`)
# ===================================================

# .. currentmodule:: qiskit_ibm_runtime

# Modules representing the IBM Quantum Provider.

# Logging
# =====================

# The IBM Quantum Provider uses the ``qiskit_ibm_runtime`` logger.

# Two environment variables can be used to control the logging:

#     * ``QISKIT_IBM_RUNTIME_LOG_LEVEL``: Specifies the log level to use, for the Qiskit
#       IBM provider modules. If an invalid level is set, the log level defaults to ``WARNING``.
#       The valid log levels are ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``
#       (case-insensitive). If the environment variable is not set, then the parent logger's level
#       is used, which also defaults to ``WARNING``.
#     * ``QISKIT_IBM_RUNTIME_LOG_FILE``: Specifies the name of the log file to use. If specified,
#       messages will be logged to the file only. Otherwise messages will be logged to the standard
#       error (usually the screen).

# For more advanced use, you can modify the logger itself. For example, to manually set the level
# to ``WARNING``::

#     import logging
#     logging.getLogger('qiskit_ibm_runtime').setLevel(logging.WARNING)

# Functions
# =========
# .. autosummary::
#     :toctree: ../stubs/

#     least_busy

# Classes
# =======
# .. autosummary::
#     :toctree: ../stubs/

#     IBMRuntimeService
#     BackendJobLimit
#     IBMBackend
#     RunnerResult

# Exceptions
# ==========
# .. autosummary::
#     :toctree: ../stubs/

#     IBMError
#     IBMProviderError
#     IBMProviderValueError
#     IBMProviderCredentialsNotFound
#     IBMProviderCredentialsInvalidFormat
#     IBMProviderCredentialsInvalidToken
#     IBMProviderCredentialsInvalidUrl
#     IBMBackendError
#     IBMBackendApiError
#     IBMBackendApiProtocolError
#     IBMBackendValueError
#     IBMProviderError
# """

import logging
from typing import List, Optional, Union
from datetime import datetime, timedelta

from qiskit.providers import BaseBackend, Backend  # type: ignore[attr-defined]

from .ibm_backend import IBMBackend
from .exceptions import *
from .utils.utils import setup_logger
from .version import __version__

from .ibm_runtime_service import IBMRuntimeService
from .runtime_job import RuntimeJob
from .runtime_program import RuntimeProgram, ParameterNamespace
from .program.user_messenger import UserMessenger
from .program.program_backend import ProgramBackend
from .program.result_decoder import ResultDecoder
from .utils.json import RuntimeEncoder, RuntimeDecoder

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


def least_busy(
    backends: List[Union[Backend, BaseBackend]],
    reservation_lookahead: Optional[int] = 60,
) -> Union[Backend, BaseBackend]:
    """Return the least busy backend from a list.

    Return the least busy available backend for those that
    have a ``pending_jobs`` in their ``status``. Note that local
    backends may not have this attribute.

    Args:
        backends: The backends to choose from.
        reservation_lookahead: A backend is considered unavailable if it
            has reservations in the next ``n`` minutes, where ``n`` is
            the value of ``reservation_lookahead``.
            If ``None``, reservations are not taken into consideration.

    Returns:
        The backend with the fewest number of pending jobs.

    Raises:
        IBMError: If the backends list is empty, or if none of the backends
            is available, or if a backend in the list
            does not have the ``pending_jobs`` attribute in its status.
    """
    if not backends:
        raise IBMError(
            "Unable to find the least_busy backend from an empty list."
        ) from None
    try:
        candidates = []
        now = datetime.now()
        for back in backends:
            backend_status = back.status()
            if not backend_status.operational or backend_status.status_msg != "active":
                continue
            if reservation_lookahead and isinstance(back, IBMBackend):
                end_time = now + timedelta(minutes=reservation_lookahead)
                try:
                    if back.reservations(now, end_time):
                        continue
                except Exception as err:  # pylint: disable=broad-except
                    logger.warning(
                        "Unable to find backend reservation information. "
                        "It will not be taken into consideration. %s",
                        str(err),
                    )
            candidates.append(back)
        if not candidates:
            raise IBMError("No backend matches the criteria.")
        return min(candidates, key=lambda b: b.status().pending_jobs)
    except AttributeError as ex:
        raise IBMError(
            "A backend in the list does not have the `pending_jobs` "
            "attribute in its status."
        ) from ex
