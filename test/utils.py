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

"""General utility functions for testing."""

import os
import logging

from qiskit import QuantumCircuit
from qiskit.qobj import QasmQobj
from qiskit.compiler import assemble, transpile
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.pulse import Schedule
from qiskit.providers.exceptions import JobError
from qiskit.providers.jobstatus import JobStatus
from qiskit_ibm.ibm_provider import IBMProvider
from qiskit_ibm.ibm_backend import IBMBackend
from qiskit_ibm.job import IBMJob


def setup_test_logging(logger: logging.Logger, filename: str):
    """Set logging to file and stdout for a logger.

    Args:
        logger: Logger object to be updated.
        filename: Name of the output file, if log to file is enabled.
    """
    # Set up formatter.
    log_fmt = ('{}.%(funcName)s:%(levelname)s:%(asctime)s:'
               ' %(message)s'.format(logger.name))
    formatter = logging.Formatter(log_fmt)

    if os.getenv('STREAM_LOG', 'true'):
        # Set up the stream handler.
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if os.getenv('FILE_LOG', 'false'):
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.setLevel(os.getenv('LOG_LEVEL', 'DEBUG'))


def most_busy_backend(provider: IBMProvider) -> IBMBackend:
    """Return the most busy backend for the provider given.

    Return the most busy available backend for those that
    have a `pending_jobs` in their `status`. Backends such as
    local backends that do not have this are not considered.

    Args:
        provider: IBM Quantum account provider.

    Returns:
        The most busy backend.
    """
    backends = provider.backends(simulator=False, operational=True)
    return max([b for b in backends if b.configuration().n_qubits >= 5],
               key=lambda b: b.status().pending_jobs)


def get_large_circuit(backend: IBMBackend) -> QuantumCircuit:
    """Return a slightly larger circuit that would run a bit longer.

    Args:
        backend: Backend on which the circuit will run.

    Returns:
        A larger circuit.
    """
    n_qubits = min(backend.configuration().n_qubits, 20)
    circuit = QuantumCircuit(n_qubits, n_qubits)
    for n in range(n_qubits-1):
        circuit.h(n)
        circuit.cx(n, n+1)
    circuit.measure(list(range(n_qubits)), list(range(n_qubits)))

    return circuit


def bell_in_qobj(backend: IBMBackend, shots: int = 1024) -> QasmQobj:
    """Return a bell circuit in Qobj format.

    Args:
        backend: Backend to use for transpiling the circuit.
        shots: Number of shots.

    Returns:
        A bell circuit in Qobj format.
    """
    return assemble(transpile(ReferenceCircuits.bell(), backend=backend),
                    backend=backend, shots=shots)


def cancel_job(job: IBMJob, verify: bool = False) -> bool:
    """Cancel a job.

    Args:
        job: Job to cancel.
        verify: Verify job status.

    Returns:
        Whether job has been cancelled.
    """
    cancelled = False
    for _ in range(2):
        # Try twice in case job is not in a cancellable state
        try:
            cancelled = job.cancel()
            if cancelled:
                if verify:
                    status = job.status()
                    assert status is JobStatus.CANCELLED, \
                        'cancel() was successful for job {} but its ' \
                        'status is {}.'.format(job.job_id(), status)
                break
        except JobError:
            pass

    return cancelled


def submit_job_bad_shots(backend: IBMBackend) -> IBMJob:
    """Submit a job that will fail due to too many shots.

    Args:
        backend: Backend to submit the job to.

    Returns:
        Submitted job.
    """
    qobj = bell_in_qobj(backend=backend)
    qobj.config.shots = 10000  # Modify the number of shots to be an invalid amount.
    job_to_fail = backend._submit_job(qobj)
    return job_to_fail


def submit_job_one_bad_instr(backend: IBMBackend) -> IBMJob:
    """Submit a job that contains one good and one bad instruction.

    Args:
        backend: Backend to submit the job to.

    Returns:
        Submitted job.
    """
    qc_new = transpile(ReferenceCircuits.bell(), backend)
    if backend.configuration().simulator:
        # Specify method so it doesn't fail at method selection.
        qobj = assemble([qc_new]*2, backend=backend, method="statevector")
    else:
        qobj = assemble([qc_new]*2, backend=backend)
    qobj.experiments[1].instructions[1].name = 'bad_instruction'
    job = backend._submit_job(qobj)
    return job


def submit_and_cancel(backend: IBMBackend) -> IBMJob:
    """Submit and cancel a job.

    Args:
        backend: Backend to submit the job to.

    Returns:
        Cancelled job.
    """
    circuit = transpile(ReferenceCircuits.bell(), backend=backend)
    job = backend.run(circuit)
    cancel_job(job, True)
    return job


def get_pulse_schedule(backend: IBMBackend) -> Schedule:
    """Return a pulse schedule."""
    config = backend.configuration()
    defaults = backend.defaults()
    inst_map = defaults.instruction_schedule_map

    # Run 2 experiments - 1 with x pulse and 1 without
    x = inst_map.get('x', 0)
    measure = inst_map.get('measure', range(config.n_qubits)) << x.duration
    ground_sched = measure
    excited_sched = x | measure
    schedules = [ground_sched, excited_sched]
    return schedules


def get_provider(
        qe_token: str,
        qe_url: str,
        default: bool = True
) -> IBMProvider:
    """Return a provider for the account.

    Args:
        qe_token: IBM Quantum token.
        qe_url: IBM Quantum auth URL.
        default: If `True`, the default open access project provider is returned.
            Otherwise, a non open access project provider is returned.

    Returns:
        A provider, as specified by `default`.
    """
    provider_to_return = IBMProvider(qe_token, url=qe_url)  # Default provider.
    if not default:
        # Get a non default provider (i.e.not the default open access project).
        providers = IBMProvider.providers()
        for provider in providers:
            if provider != provider_to_return:
                provider_to_return = provider
                break
    IBMProvider._disable_account()

    return provider_to_return
