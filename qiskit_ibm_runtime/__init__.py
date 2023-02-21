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

Modules related to Qiskit Runtime IBM Client.

Qiskit Runtime is a new architecture that
streamlines computations requiring many iterations. These experiments will
execute significantly faster within its improved hybrid quantum/classical process.

Primitives and sessions
-----------------------

Qiskit Runtime has two predefined primitive programs: ``Sampler`` and ``Estimator``.
These primitives provide a simplified interface for performing foundational quantum
computing tasks while also accounting for the latest developments in
quantum hardware and software.

Qiskit Runtime also has the concept of a session. Jobs submitted within a session are
prioritized by the scheduler, and parameter data is cached for reuse. A session
allows you to make iterative calls to the quantum computer more efficiently.

Below is an example of using primitives within a session::

    from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator, Options
    from qiskit.test.reference_circuits import ReferenceCircuits
    from qiskit.circuit.library import RealAmplitudes
    from qiskit.quantum_info import SparsePauliOp

    # Initialize account.
    service = QiskitRuntimeService()

    # Set options, which can be overwritten at job level.
    options = Options(optimization_level=3)

    # Prepare inputs.
    bell = ReferenceCircuits.bell()
    psi = RealAmplitudes(num_qubits=2, reps=2)
    H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
    theta = [0, 1, 1, 2, 3, 5]

    with Session(service=service, backend="ibmq_qasm_simulator") as session:
        # Submit a request to the Sampler primitive within the session.
        sampler = Sampler(session=session, options=options)
        job = sampler.run(circuits=bell)
        print(f"Sampler results: {job.result()}")

        # Submit a request to the Estimator primitive within the session.
        estimator = Estimator(session=session, options=options)
        job = estimator.run(
            circuits=[psi], observables=[H1], parameter_values=[theta]
        )
        print(f"Estimator results: {job.result()}")
        # Close the session only if all jobs are finished and you don't need to run more in the session.
        session.close()

Backend data
------------

:class:`QiskitRuntimeService` also has methods, such as :meth:`backend`,
:meth:`backends`, and :meth:`least_busy`, that allow you to query for a target
backend to use. These methods return one or more :class:`IBMBackend` instances
that contains methods and attributes describing the backend.

Supplementary Information
-------------------------

.. dropdown:: Account initialization
   :animate: fade-in-slide-down

    You need to initialize your account before you can start using the Qiskit Runtime service.
    This is done by initializing a :class:`QiskitRuntimeService` instance with your
    account credentials. If you don't want to pass in the credentials each time, you
    can use the :meth:`QiskitRuntimeService.save_account` method to save the credentials
    on disk.

    Qiskit Runtime is available on both IBM Cloud and IBM Quantum, and you can specify
    ``channel="ibm_cloud"`` for IBM Cloud and ``channel="ibm_quantum"`` for IBM Quantum. The default
    is IBM Cloud.

.. dropdown:: Runtime Jobs
   :animate: fade-in-slide-down

    When you use the ``run()`` method of the :class:`Sampler` or :class:`Estimator`
    to invoke the primitive program, a
    :class:`RuntimeJob` instance is returned. This class has all the basic job
    methods, such as :meth:`RuntimeJob.status`, :meth:`RuntimeJob.result`, and
    :meth:`RuntimeJob.cancel`.

.. dropdown:: Logging
   :animate: fade-in-slide-down

    ``qiskit-ibm-runtime`` uses the ``qiskit_ibm_runtime`` logger.

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

.. dropdown:: Invoking a non-primitive program
   :animate: fade-in-slide-down

    Qiskit Runtime has a handful of predefined programs in addition to the primitives.
    Unlike the primitives, these programs don't have special classes defined and
    can be invoked in a generic way. For example::

        from qiskit_ibm_runtime import QiskitRuntimeService

        # Initialize account.
        service = QiskitRuntimeService()

        # Configure backend options.
        options = {"backend": "ibmq_qasm_simulator"}

        # Prepare inputs.
        runtime_inputs = {"iterations": 1}

        # Invoke the "hello-world" program.
        job = service.run(program_id="hello-world",
                          options=options,
                          inputs=runtime_inputs)
        # Get runtime job result.
        print(job.result())

.. dropdown:: Interim and final results
   :animate: fade-in-slide-down

    Some runtime programs provide interim results that inform you about program
    progress. You can choose to stream the interim results and final result when you run the
    program by passing in the ``callback`` parameter, or at a later time using
    the :meth:`RuntimeJob.stream_results` method. For example::

        from qiskit_ibm_runtime import QiskitRuntimeService

        service = QiskitRuntimeService()
        options = {"backend": "ibmq_qasm_simulator"}
        runtime_inputs = {"iterations": 2}

        def result_callback(job_id, result):
            print(result)

        # Stream results as soon as the job starts running.
        job = service.run(program_id="hello-world",
                          options=options,
                          inputs=runtime_inputs,
                          callback=result_callback)
        print(job.result())

.. dropdown:: Uploading a program
   :animate: fade-in-slide-down

    Authorized users can upload their custom Qiskit Runtime programs.
    A Qiskit Runtime program is a piece of Python
    code and its metadata that takes certain inputs, performs
    quantum and maybe classical processing, and returns the results.

    Files related to writing a runtime program are in the
    ``qiskit_ibm_runtime/program`` directory.

Classes
==========================
.. autosummary::
   :toctree: ../stubs/

   QiskitRuntimeService
   Estimator
   Sampler
   Session
   IBMBackend
   RuntimeJob
   RuntimeProgram
   ParameterNamespace
   RuntimeOptions
   RuntimeEncoder
   RuntimeDecoder
"""

import logging

from .qiskit_runtime_service import QiskitRuntimeService
from .ibm_backend import IBMBackend
from .runtime_job import RuntimeJob
from .runtime_program import RuntimeProgram, ParameterNamespace
from .runtime_options import RuntimeOptions
from .utils.json import RuntimeEncoder, RuntimeDecoder
from .session import Session  # pylint: disable=cyclic-import

from .exceptions import *
from .utils.utils import setup_logger
from .version import __version__

from .estimator import Estimator
from .sampler import Sampler
from .options import Options

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
