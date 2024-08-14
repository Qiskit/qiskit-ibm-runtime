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
import itertools
import unittest
from unittest import mock
from typing import Dict, Optional, Any
from datetime import datetime
from ddt import data, unpack

from qiskit.circuit import QuantumCircuit, QuantumRegister, ClassicalRegister, Parameter
from qiskit.compiler import transpile
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.backend import Backend
from qiskit.quantum_info import SparsePauliOp, Pauli
from qiskit_ibm_runtime import (
    QiskitRuntimeService,
    Session,
    EstimatorV2,
    SamplerV2,
    Batch,
)
from qiskit_ibm_runtime.fake_provider import FakeManila
from qiskit_ibm_runtime.hub_group_project import HubGroupProject
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.models import (
    BackendStatus,
    BackendProperties,
    BackendConfiguration,
)
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
            status == "CANCELLED"
        ), "cancel() was successful for job {} but its " "status is {}.".format(
            job.job_id(), status
        )
        return True
    except RuntimeInvalidStateError:
        if job.status() in ["DONE", "CANCELLED", "ERROR"]:
            logger.warning("Unable to cancel job because it's already done.")
            return False
        raise


def wait_for_status(job, status, poll_time=1, time_out=20):
    """Wait for job to reach a certain status."""
    wait_time = 1 if status == "QUEUED" else poll_time
    while job.status() not in ["DONE", "CANCELLED", "ERROR"] and time_out > 0:
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


def dict_keys_equal(dict1: dict, dict2: dict, exclude_keys: list = None) -> bool:
    """Recursively determine whether the dictionaries have the same keys.

    Args:
        dict1: First dictionary.
        dict2: Second dictionary.
        exclude_keys: A list of keys in dictionary 1 to be excluded.

    Returns:
        Whether the two dictionaries have the same keys.
    """
    exclude_keys = exclude_keys or []
    for key, val in dict1.items():
        if key in exclude_keys:
            continue
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
    faulty_q1_property: Optional[int] = None,
) -> IBMBackend:
    """Create an IBMBackend that has faulty qubits and/or edges.

    Args:
        model_backend: Fake backend to model after.
        faulty_qubit: Faulty qubit.
        faulty_edge: Faulty edge, a tuple of (gate, qubits)
        faulty_q1_property: Faulty Q1 property.

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

    if faulty_q1_property:
        properties["qubits"][faulty_q1_property] = [
            q for q in properties["qubits"][faulty_q1_property] if q["name"] != "T1"
        ]

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


def get_mocked_backend(
    name: str = "ibm_gotham",
    configuration: Optional[Dict] = None,
    properties: Optional[Dict] = None,
    defaults: Optional[Dict] = None,
) -> IBMBackend:
    """Return a mock backend."""

    mock_service = mock.MagicMock(spec=QiskitRuntimeService)
    mock_service._channel_strategy = None
    mock_api_client = mock.MagicMock()
    mock_service._api_client = mock_api_client

    configuration = (
        FakeManila().configuration()  # type: ignore[assignment]
        if configuration is None
        else BackendConfiguration.from_dict(configuration)
    )

    mock_api_client.backend_properties = lambda *args, **kwargs: properties
    mock_api_client.backend_pulse_defaults = lambda *args, **kwargs: defaults
    mock_backend = IBMBackend(
        configuration=configuration, service=mock_service, api_client=mock_api_client
    )
    mock_backend.name = name
    mock_backend._instance = None
    mock_service.backend = lambda name, **kwargs: (
        mock_backend if name == mock_backend.name else None
    )

    return mock_backend


def get_mocked_session(backend: Any = None) -> mock.MagicMock:
    """Return a mocked session object."""
    session = mock.MagicMock(spec=Session)
    session._instance = None
    session._backend = backend or get_mocked_backend()
    session._service = getattr(backend, "service", None) or mock.MagicMock(
        spec=QiskitRuntimeService
    )
    return session


def get_mocked_batch(backend: Any = None) -> mock.MagicMock:
    """Return a mocked batch object."""
    batch = mock.MagicMock(spec=Batch)
    batch._instance = None
    batch._backend = backend or get_mocked_backend()
    batch._service = getattr(backend, "service", None) or mock.MagicMock(spec=QiskitRuntimeService)
    return batch


def submit_and_cancel(backend: IBMBackend, logger: logging.Logger) -> RuntimeJob:
    """Submit and cancel a job.

    Args:
        backend: Backend to submit the job to.

    Returns:
        Cancelled job.
    """
    circuit = transpile(bell(), backend=backend)
    sampler = SamplerV2(backend)
    job = sampler.run([circuit])
    cancel_job_safe(job, logger=logger)
    return job


class Case(dict):
    """<no description>"""


def generate_cases(docstring, dsc=None, name=None, **kwargs):
    """Combines kwargs in Cartesian product and creates Case with them"""
    ret = []
    keys = kwargs.keys()
    vals = kwargs.values()
    for values in itertools.product(*vals):
        case = Case(zip(keys, values))
        if docstring is not None:
            setattr(case, "__doc__", docstring.format(**case))
        if dsc is not None:
            setattr(case, "__doc__", dsc.format(**case))
        if name is not None:
            setattr(case, "__name__", name.format(**case))
        ret.append(case)
    return ret


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


def bell():
    """Return a Bell circuit."""
    quantum_register = QuantumRegister(2, name="qr")
    classical_register = ClassicalRegister(2, name="cr")
    quantum_circuit = QuantumCircuit(quantum_register, classical_register, name="bell")
    quantum_circuit.h(quantum_register[0])
    quantum_circuit.cx(quantum_register[0], quantum_register[1])
    quantum_circuit.measure(quantum_register, classical_register)

    return quantum_circuit


def get_transpiled_circuit(backend, num_qubits=2, measure=False):
    """Return a transpiled circuit."""
    circ = QuantumCircuit(num_qubits)
    circ.h(0)
    for idx in range(num_qubits - 2):
        circ.cx(idx, idx + 1)
    if measure:
        circ.measure_all()
    return transpile(circ, backend=backend)


def get_primitive_inputs(primitive, backend=None, num_sets=1):
    """Return primitive specific inputs."""
    backend = backend or FakeManila()
    theta = Parameter("θ")
    circ = QuantumCircuit(2)
    circ.h(0)
    circ.cx(0, 1)
    circ.ry(theta, 0)

    circ = transpile(circ, backend=backend)
    obs = SparsePauliOp.from_list([("IZ", 1)])
    obs = obs.apply_layout(circ.layout, num_qubits=circ.num_qubits)
    param_val = [0.1]

    if isinstance(primitive, EstimatorV2):
        return {"pubs": [(circ, [obs], [param_val])] * num_sets}
    elif isinstance(primitive, SamplerV2):
        circ.measure_all()
        return {"pubs": [(circ, param_val)] * num_sets}
    else:
        raise ValueError(f"Invalid primitive type {type(primitive)}")


def transpile_pubs(in_pubs, backend, program):
    """Return pubs with transformed circuits and observables."""
    t_pubs = []
    for pub in in_pubs:
        t_circ = transpile(pub[0], backend=backend)
        if program == "estimator":
            t_obs = remap_observables(pub[1], t_circ)
            t_pub = [t_circ, t_obs]
            for elem in pub[2:]:
                t_pub.append(elem)
        if program == "sampler":
            if len(pub) == 2:
                t_pub = [t_circ, pub[1]]
            else:
                t_pub = [t_circ]
        t_pubs.append(tuple(t_pub))
    return t_pubs


def remap_observables(observables, isa_circuit):
    """Remap observables based on input cirucit."""

    def _convert_paul_or_str(_obs):
        if isinstance(_obs, str):
            return _obs + "I" * (len(layout.input_qubit_mapping) - len(_obs))
        return Pauli("X" * (len(layout.input_qubit_mapping)))

    out_obs = []
    layout = isa_circuit.layout
    for obs in observables:
        if isinstance(obs, (str, Pauli)):
            out_obs.append(_convert_paul_or_str(obs))
        elif isinstance(obs, SparsePauliOp):
            out_obs.append(obs.apply_layout(layout, num_qubits=isa_circuit.num_qubits))
        elif isinstance(obs, dict):
            mapped = {_convert_paul_or_str(key): val for key, val in obs.items()}
            out_obs.append(mapped)
        else:
            raise ValueError(f"Observable of type {type(obs)} is not supported.")

    return out_obs


class MockSession(Session):
    """Mock for session class"""

    _circuits_map: Dict[str, QuantumCircuit] = {}
    _instance = None
