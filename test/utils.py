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
import time
import unittest
from unittest import mock
from typing import Dict, Optional, Any
from datetime import datetime

from ddt import data, unpack

from qiskit.circuit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.test.utils import generate_cases
from qiskit.providers.jobstatus import JOB_FINAL_STATES, JobStatus
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.models import BackendStatus, BackendProperties
from qiskit.providers.backend import Backend
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime.hub_group_project import HubGroupProject
from qiskit_ibm_runtime import QiskitRuntimeService, Session
from qiskit_ibm_runtime.estimator import Estimator
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.runtime_job import RuntimeJob
from qiskit_ibm_runtime.exceptions import RuntimeInvalidStateError


def setup_test_logging(logger: logging.Logger, filename: str) -> None:
    """Set logging to file and stdout for a logger.

    Args:
        logger: Logger object to be updated.
        filename: Name of the output file, if log to file is enabled.
    """
    # Set up formatter.
    log_fmt = "{}.%(funcName)s:%(levelname)s:%(asctime)s:" " %(message)s".format(logger.name)
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
    service: QiskitRuntimeService,
    instance: Optional[str] = None,
) -> IBMBackend:
    """Return the most busy backend for the provider given.

    Return the most busy available backend for those that
    have a `pending_jobs` in their `status`. Backends such as
    local backends that do not have this are not considered.

    Args:
        service: Qiskit Runtime Service.
        instance: The instance in the hub/group/project format.

    Returns:
        The most busy backend.
    """
    backends = service.backends(simulator=False, operational=True, instance=instance)
    return max(
        (b for b in backends if b.configuration().n_qubits >= 5),
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
    for qubit in range(n_qubits - 1):
        circuit.h(qubit)
        circuit.cx(qubit, qubit + 1)
    circuit.measure(list(range(n_qubits)), list(range(n_qubits)))

    return circuit


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
    service = QiskitRuntimeService(
        channel="ibm_quantum", token=qe_token, url=qe_url
    )  # Default hub/group/project.
    open_hgp = service._get_hgp()  # Open access hgp
    hgp_to_return = open_hgp
    if not default:
        # Get a non default hgp (i.e. not the default open access hgp).
        hgps = service._get_hgps()  # type: ignore
        for hgp in hgps:
            if hgp != open_hgp:
                hgp_to_return = hgp
                break
    return hgp_to_return


def cancel_job_safe(job: RuntimeJob, logger: logging.Logger) -> bool:
    """Cancel a runtime job."""
    try:
        job.cancel()
        status = job.status()
        assert (
            status is JobStatus.CANCELLED
        ), "cancel() was successful for job {} but its " "status is {}.".format(
            job.job_id(), status
        )
        return True
    except RuntimeInvalidStateError:
        if job.status() in JOB_FINAL_STATES:
            logger.warning("Unable to cancel job because it's already done.")
            return False
        raise


def wait_for_status(job, status, poll_time=1, time_out=20):
    """Wait for job to reach a certain status."""
    wait_time = 1 if status == JobStatus.QUEUED else poll_time
    while job.status() not in JOB_FINAL_STATES + (status,) and time_out > 0:
        time.sleep(wait_time)
        time_out -= wait_time
    if job.status() != status:
        raise unittest.SkipTest(f"Job {job.job_id()} unable to reach status {status}.")


def get_real_device(service):
    """Get a real device for the service."""
    try:
        return service.least_busy(simulator=False).name
    except QiskitBackendNotFoundError:
        raise unittest.SkipTest("No real device")  # cloud has no real device


def mock_wait_for_final_state(service, job):
    """replace `wait_for_final_state` with a mock function"""
    return mock.patch.object(
        RuntimeJob,
        "wait_for_final_state",
        side_effect=service._api_client.wait_for_final_state(job.job_id()),
    )


def dict_paritally_equal(dict1: Dict, dict2: Dict) -> bool:
    """Determine whether all keys in dict2 are in dict1 and have same values."""
    for key, val in dict2.items():
        if isinstance(val, dict):
            if not dict_paritally_equal(dict1.get(key, {}), val):
                return False
        elif key not in dict1 or val != dict1[key]:
            return False

    return True


def flat_dict_partially_equal(dict1: dict, dict2: dict) -> bool:
    """Flat the dictionaries then determine whether all keys in dict2 are
    in dict1 and have the same values."""

    def _flat_dict(in_dict, out_dict):
        for key_, val_ in in_dict.items():
            if isinstance(val_, dict):
                _flat_dict(val_, out_dict)
            else:
                out_dict[key_] = val_

    flat_dict1: dict = {}
    flat_dict2: dict = {}
    _flat_dict(dict1, flat_dict1)
    _flat_dict(dict2, flat_dict2)

    for key, val in flat_dict2.items():
        if key not in flat_dict1 or flat_dict1[key] != val:
            return False
    return True


def dict_keys_equal(dict1: dict, dict2: dict) -> bool:
    """Determine whether the dictionaries have the same keys."""
    for key, val in dict1.items():
        if key not in dict2:
            return False
        if isinstance(val, dict):
            if not dict_keys_equal(val, dict2[key]):
                return False

    return True


def create_faulty_backend(
    model_backend: Backend,
    faulty_qubit: Optional[int] = None,
    faulty_edge: Optional[tuple] = None,
) -> IBMBackend:
    """Create an IBMBackend that has faulty qubits and/or edges.

    Args:
        model_backend: Fake backend to model after.
        faulty_qubit: Faulty qubit.
        faulty_edge: Faulty edge, a tuple of (gate, qubits)

    Returns:
        An IBMBackend with faulty qubits/edges.
    """

    properties = model_backend.properties().to_dict()

    if faulty_qubit:
        properties["qubits"][faulty_qubit].append(
            {"date": datetime.now(), "name": "operational", "unit": "", "value": 0}
        )

    if faulty_edge:
        gate, qubits = faulty_edge
        for gate_obj in properties["gates"]:
            if gate_obj["gate"] == gate and gate_obj["qubits"] == qubits:
                gate_obj["parameters"].append(
                    {
                        "date": datetime.now(),
                        "name": "operational",
                        "unit": "",
                        "value": 0,
                    }
                )

    out_backend = IBMBackend(
        configuration=model_backend.configuration(),
        service=mock.MagicMock(),
        api_client=None,
        instance=None,
    )

    out_backend.status = lambda: BackendStatus(  # type: ignore[assignment]
        backend_name="foo",
        backend_version="1.0",
        operational=True,
        pending_jobs=0,
        status_msg="",
    )
    out_backend.properties = lambda: BackendProperties.from_dict(properties)  # type: ignore
    return out_backend


def get_mocked_backend(name: str = "ibm_gotham") -> Any:
    """Return a mock backend."""
    mock_backend = mock.MagicMock(spec=IBMBackend)
    mock_backend.name = name
    mock_backend._instance = None

    mock_service = mock.MagicMock()
    mock_backend.service = mock_service

    return mock_backend


def submit_and_cancel(backend: IBMBackend, logger: logging.Logger) -> RuntimeJob:
    """Submit and cancel a job.

    Args:
        backend: Backend to submit the job to.

    Returns:
        Cancelled job.
    """
    circuit = transpile(ReferenceCircuits.bell(), backend=backend)
    job = backend.run(circuit)
    cancel_job_safe(job, logger=logger)
    return job


def combine(**kwargs):
    """Decorator to create combinations and tests
    @combine(level=[0, 1, 2, 3],
             circuit=[a, b, c, d],
             dsc='Test circuit {circuit.__name__} with level {level}',
             name='{circuit.__name__}_level{level}')
    """

    def deco(func):
        return data(*generate_cases(docstring=func.__doc__, **kwargs))(unpack(func))

    return deco


def get_primitive_inputs(primitive, num_sets=1):
    """Return primitive specific inputs."""
    circ = QuantumCircuit(2, 2)
    circ.h(0)
    circ.cx(0, 1)
    obs = SparsePauliOp.from_list([("IZ", 1)])

    if isinstance(primitive, Estimator):
        return {"tasks": [(circ, [obs])] * num_sets}

    circ.measure_all()
    return {"tasks": [(circ,)] * num_sets}


class MockSession(Session):
    """Mock for session class"""

    _circuits_map: Dict[str, QuantumCircuit] = {}
    _instance = None
