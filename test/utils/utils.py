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
from typing import Optional

from qiskit import QuantumCircuit
from qiskit.qobj import QasmQobj
from qiskit.compiler import assemble, transpile
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.pulse import Schedule
from qiskit_ibm_runtime.hub_group_project import HubGroupProject
from qiskit_ibm_runtime import IBMRuntimeService
from qiskit_ibm_runtime.ibm_backend import IBMBackend


def setup_test_logging(logger: logging.Logger, filename: str):
    """Set logging to file and stdout for a logger.

    Args:
        logger: Logger object to be updated.
        filename: Name of the output file, if log to file is enabled.
    """
    # Set up formatter.
    log_fmt = "{}.%(funcName)s:%(levelname)s:%(asctime)s:" " %(message)s".format(
        logger.name
    )
    formatter = logging.Formatter(log_fmt)

    if os.getenv("STREAM_LOG", "true").lower() == "true":
        # Set up the stream handler.
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if os.getenv("FILE_LOG", "false").lower() == "true":
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG"))


def most_busy_backend(
    service: IBMRuntimeService,
    hub: Optional[str] = None,
    group: Optional[str] = None,
    project: Optional[str] = None,
) -> IBMBackend:
    """Return the most busy backend for the provider given.

    Return the most busy available backend for those that
    have a `pending_jobs` in their `status`. Backends such as
    local backends that do not have this are not considered.

    Args:
        service: IBM Quantum account provider.
        hub: Name of the hub.
        group: Name of the group.
        project: Name of the project.

    Returns:
        The most busy backend.
    """
    backends = service.backends(
        simulator=False, operational=True, hub=hub, group=group, project=project
    )
    return max(
        [b for b in backends if b.configuration().n_qubits >= 5],
        key=lambda b: b.status().pending_jobs,
    )


def get_large_circuit(backend: IBMBackend) -> QuantumCircuit:
    """Return a slightly larger circuit that would run a bit longer.

    Args:
        backend: Backend on which the circuit will run.

    Returns:
        A larger circuit.
    """
    n_qubits = min(backend.configuration().n_qubits, 20)
    circuit = QuantumCircuit(n_qubits, n_qubits)
    for n in range(n_qubits - 1):
        circuit.h(n)
        circuit.cx(n, n + 1)
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
    return assemble(
        transpile(ReferenceCircuits.bell(), backend=backend),
        backend=backend,
        shots=shots,
    )


def get_pulse_schedule(backend: IBMBackend) -> Schedule:
    """Return a pulse schedule."""
    config = backend.configuration()
    defaults = backend.defaults()
    inst_map = defaults.instruction_schedule_map

    # Run 2 experiments - 1 with x pulse and 1 without
    x = inst_map.get("x", 0)
    measure = inst_map.get("measure", range(config.n_qubits)) << x.duration
    ground_sched = measure
    excited_sched = x | measure
    schedules = [ground_sched, excited_sched]
    return schedules


def get_hgp(qe_token: str, qe_url: str, default: bool = True) -> HubGroupProject:
    """Return a HubGroupProject for the account.

    Args:
        qe_token: IBM Quantum token.
        qe_url: IBM Quantum auth URL.
        default: If `True`, the default open access hgp is returned.
            Otherwise, a non open access hgp is returned.

    Returns:
        A HubGroupProject, as specified by `default`.
    """
    service = IBMRuntimeService(
        auth="legacy", token=qe_token, locator=qe_url
    )  # Default hub/group/project.
    open_hgp = service._get_hgp()  # Open access hgp
    hgp_to_return = open_hgp
    if not default:
        # Get a non default hgp (i.e. not the default open access hgp).
        hgps = service._get_hgps()
        for hgp in hgps:
            if hgp != open_hgp:
                hgp_to_return = hgp
                break
    return hgp_to_return
