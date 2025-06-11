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

"""General utility functions."""

from __future__ import annotations
import copy
import keyword
import logging
import os
import re
from queue import Queue
from threading import Condition
from typing import List, Optional, Any, Dict, Union, Tuple, Set
from urllib.parse import urlparse
from itertools import chain
import numpy as np

import requests
from ibm_cloud_sdk_core.authenticators import (  # pylint: disable=import-error
    IAMAuthenticator,
)
from ibm_platform_services import ResourceControllerV2  # pylint: disable=import-error
from qiskit.circuit import QuantumCircuit, ControlFlowOp, ParameterExpression, Parameter
from qiskit.circuit.delay import Delay
from qiskit.circuit.gate import Instruction
from qiskit.circuit.library.standard_gates import (
    RZGate,
    U1Gate,
    PhaseGate,
)
from qiskit.transpiler import Target
from qiskit.providers.backend import BackendV2
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.primitives.containers.sampler_pub import SamplerPub


def is_simulator(backend: BackendV2) -> bool:
    """Return true if the backend is a simulator.

    Args:
        backend: Backend to check.

    Returns:
        True if backend is a simulator.
    """
    if hasattr(backend, "configuration"):
        return getattr(backend.configuration(), "simulator", False)
    return getattr(backend, "simulator", False)


def _is_isa_circuit_helper(circuit: QuantumCircuit, target: Target, qubit_map: Dict) -> str:
    """
    A section of is_isa_circuit, separated to allow recursive calls
    within blocks of conditional operations.
    """
    for instruction in circuit.data:
        operation = instruction.operation

        name = operation.name
        qargs = tuple(qubit_map[bit] for bit in instruction.qubits)
        if not target.instruction_supported(name, qargs) and name != "barrier":
            return (
                f"The instruction {name} on qubits {qargs} is not supported by the target system."
            )

        # rzz gate is calibrated only for the range [0, pi/2].
        # We allow an angle value of a bit more than pi/2, to compensate floating point rounding
        # errors (beyond pi/2 does not trigger an error down the stack, only may become less
        # accurate).
        if (
            name == "rzz"
            and not isinstance((param := instruction.operation.params[0]), ParameterExpression)
            and (param < 0.0 or param > np.pi / 2 + 1e-10)
        ):
            return (
                f"The instruction {name} on qubits {qargs} is supported only for angles in the "
                f"range [0, pi/2], but an angle ({param}) outside of this range has been requested."
            )

        if isinstance(operation, ControlFlowOp):
            for sub_circ in operation.blocks:
                inner_map = {
                    inner: qubit_map[outer]
                    for outer, inner in zip(instruction.qubits, sub_circ.qubits)
                }
                sub_string = _is_isa_circuit_helper(sub_circ, target, inner_map)
                if sub_string:
                    return sub_string

    return ""


def is_isa_circuit(circuit: QuantumCircuit, target: Target) -> str:
    """Checks if the circuit is an ISA circuit, meaning that it has a layout and that it
    only uses instructions that exist in the target.

    Args:
        circuit: A single QuantumCircuit
        target: The backend target

    Returns:
        Message on why the circuit is not an ISA circuit, if applicable.
    """
    if circuit.num_qubits > target.num_qubits:
        return (
            f"The circuit has {circuit.num_qubits} qubits "
            f"but the target system requires {target.num_qubits} qubits."
        )

    qubit_map = {qubit: index for index, qubit in enumerate(circuit.qubits)}
    return _is_isa_circuit_helper(circuit, target, qubit_map)


def _is_valid_rzz_pub_helper(circuit: QuantumCircuit) -> Union[str, Set[Parameter]]:
    """
    For rzz gates:
    - Verify that numeric angles are in the range [0, pi/2]
    - Collect parameterized angles

    Returns one of the following:
    - A string, containing an error message, if a numeric angle is outside of the range [0, pi/2]
    - A list of names of all the parameters that participate in an rzz gate

    Note: we check for parametrized rzz gates inside control flow operation, although fractional
    gates are actually impossible in combination with dynamic circuits. This is in order to remain
    correct if this restriction is removed at some point.
    """
    angle_params = set()

    for instruction in circuit.data:
        operation = instruction.operation

        # rzz gate is calibrated only for the range [0, pi/2].
        # We allow an angle value of a bit more than pi/2, to compensate floating point rounding
        # errors (beyond pi/2 does not trigger an error down the stack, only may become less
        # accurate).
        if operation.name == "rzz":
            angle = instruction.operation.params[0]
            if isinstance(angle, ParameterExpression):
                angle_params.add(angle)
            elif angle < 0.0 or angle > np.pi / 2 + 1e-10:
                return (
                    "The instruction rzz is supported only for angles in the "
                    f"range [0, pi/2], but an angle ({angle}) outside of this "
                    "range has been requested."
                )

        if isinstance(operation, ControlFlowOp):
            for sub_circ in operation.blocks:
                body_result = _is_valid_rzz_pub_helper(sub_circ)
                if isinstance(body_result, str):
                    return body_result
                angle_params.update(body_result)

    return angle_params


def is_valid_rzz_pub(pub: Union[EstimatorPub, SamplerPub]) -> str:
    """Verify that all rzz angles are in the range [0, pi/2].

    Args:
        pub: A pub to be checked

    Returns:
        An empty string if all angles are valid, otherwise an error message.
    """
    helper_result = _is_valid_rzz_pub_helper(pub.circuit)

    if isinstance(helper_result, str):
        return helper_result

    if len(helper_result) == 0:
        return ""

    # helper_result is a set of parameter expressions
    rzz_params = list(helper_result)

    # gather all parameter names, in order
    pub_params = np.array(list(chain.from_iterable(pub.parameter_values.data)))

    # first axis will be over flattened shape, second axis over circuit parameters
    arr = pub.parameter_values.ravel().as_array()

    for param_exp in rzz_params:
        param_names = [param.name for param in param_exp.parameters]

        col_indices = [np.where(pub_params == param_name)[0][0] for param_name in param_names]
        # col_indices is the indices of columns in the parameter value array that have to be checked

        # project only to the parameters that have to be checked
        projected_arr = arr[:, col_indices]

        for row in projected_arr:
            angle = float(param_exp.bind(dict(zip(param_exp.parameters, row))))
            if angle < 0.0 or angle > np.pi / 2 + 1e-10:
                vals_msg = ", ".join(
                    [f"{param_name}={param_val}" for param_name, param_val in zip(param_names, row)]
                )
                return (
                    "The instruction rzz is supported only for angles in the "
                    f"range [0, pi/2], but an angle ({angle}) outside of this range has been "
                    f"requested; via parameter value(s) {vals_msg}, substituted in parameter "
                    f"expression {param_exp}."
                )

    return ""


def are_circuits_dynamic(circuits: List[QuantumCircuit], qasm_default: bool = True) -> bool:
    """Checks if the input circuits are dynamic."""
    for circuit in circuits:
        if isinstance(circuit, str):
            return qasm_default  # currently do not verify QASM inputs
        for inst in circuit:
            if (
                isinstance(inst.operation, ControlFlowOp)
                or getattr(inst.operation, "condition", None) is not None
            ):
                return True
    return False


def is_fractional_gate(gate: Instruction) -> bool:
    """Test if a gate is considered fractional by IBM

    Fractional gates produce a rotation based on a continuous input parameter
    and require a non-zero gate duration. The latter distinction excludes gates
    like ``RZGate`` which can be implemented in software with no duration. The
    fractional gate definition is based on the current IBM compiler system
    which currently can not use fractional gates and dynamic circuit
    instructions in the same job. In that sense, this function is really
    testing if a gate is currently incompatible with dynamic circuit
    instructions for IBM's compiler.

    Args:
        gate: The instruction to test for status as a fractional gate

    Returns:
        True if the gate is a fractional gate
    """
    # In IBM architecture these gates are virtual-Z and delay,
    # which don't change control parameter with its gate parameter.
    exclude_list = (RZGate, PhaseGate, U1Gate, Delay)
    return len(gate.params) > 0 and not isinstance(gate, exclude_list)


def get_iam_api_url(cloud_url: str) -> str:
    """Computes the IAM API URL for the given IBM Cloud URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://iam.{parsed_url.hostname}"


def get_global_search_api_url(cloud_url: str) -> str:
    """Compute the GlobalSearchV2 API URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://api.global-search-tagging.{parsed_url.hostname}"


def get_global_catalog_api_url(cloud_url: str) -> str:
    """Compute the GlobalCatalogV1 API URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://globalcatalog.{parsed_url.hostname}/api/v1"


def get_resource_controller_api_url(cloud_url: str) -> str:
    """Computes the Resource Controller API URL for the given IBM Cloud URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://resource-controller.{parsed_url.hostname}"


def resolve_crn(channel: str, url: str, instance: str, token: str) -> List[str]:
    """Resolves the Cloud Resource Name (CRN) for the given cloud account."""
    if channel not in ["ibm_cloud", "ibm_quantum_platform"]:
        raise ValueError("CRN value can only be resolved for cloud accounts.")

    if is_crn(instance):
        # no need to resolve CRN value by name
        return [instance]
    else:
        with requests.Session() as session:
            # resolve CRN value based on the provided service name
            authenticator = IAMAuthenticator(token, url=get_iam_api_url(url))
            client = ResourceControllerV2(authenticator=authenticator)
            client.set_service_url(get_resource_controller_api_url(url))
            client.set_http_client(session)
            list_response = client.list_resource_instances(name=instance)
            result = list_response.get_result()
            row_count = result["rows_count"]
            if row_count == 0:
                return []
            else:
                return list(map(lambda resource: resource["crn"], result["resources"]))


def is_crn(locator: str) -> bool:
    """Check if a given value is a CRN (Cloud Resource Name).

    Args:
        locator: The value to check.

    Returns:
        Whether the input is a CRN.
    """
    return isinstance(locator, str) and locator.startswith("crn:")


def default_runtime_url_resolver(
    url: str, instance: str, private_endpoint: bool = False, channel: str = "ibm_quantum_platform"
) -> str:
    """Computes the Runtime API base URL based on the provided input parameters.

    Args:
        url: The URL.
        instance: The instance.
        private_endpoint: Connect to private API URL.

    Returns:
        Runtime API base URL
    """

    # ibm_quantum: no need to resolve runtime API URL
    api_host = url

    # cloud: compute runtime API URL based on crn and URL
    if is_crn(instance) and not _is_experimental_runtime_url(url):
        parsed_url = urlparse(url)
        if private_endpoint:
            api_host = (
                f"{parsed_url.scheme}://private.{_location_from_crn(instance)}"
                f".quantum-computing.{parsed_url.hostname}"
            )
        elif channel == "ibm_quantum_platform":
            # ibm_quantum_platform url
            region = _location_from_crn(instance)
            region_prefix = "" if region == "us-east" else f"{region}."
            api_host = (
                f"{parsed_url.scheme}://{region_prefix}" f"quantum.{parsed_url.hostname}/api/v1"
            )
        else:
            # ibm_cloud url
            api_host = (
                f"{parsed_url.scheme}://{_location_from_crn(instance)}"
                f".quantum-computing.{parsed_url.hostname}"
            )

    return api_host


def _is_experimental_runtime_url(url: str) -> bool:
    """Checks if the provided url points to an experimental runtime cluster.
    This type of URLs is used for internal development purposes only.

    Args:
        url: The URL.
    """
    return isinstance(url, str) and "experimental" in url


def _location_from_crn(crn: str) -> str:
    """Computes the location from a given CRN.

    Args:
        crn: A CRN (format: https://cloud.ibm.com/docs/account?topic=account-crn#format-crn)

    Returns:
        The location.
    """
    pattern = "(.*?):(.*?):(.*?):(.*?):(.*?):(.*?):.*"
    return re.search(pattern, crn).group(6)


def cname_from_crn(crn: str) -> str:
    """Computes the CNAME ('bluemix' or 'staging') from a given CRN.

    Args:
        crn: A CRN (format: https://cloud.ibm.com/docs/account?topic=account-crn#format-crn)

    Returns:
        The location.
    """
    if is_crn(crn):
        pattern = "(.*?):(.*?):(.*?):(.*?):(.*?):(.*?):.*"
        return re.search(pattern, crn).group(3)
    return None


def to_python_identifier(name: str) -> str:
    """Convert a name to a valid Python identifier.

    Args:
        name: Name to be converted.

    Returns:
        Name that is a valid Python identifier.
    """
    # Python identifiers can only contain alphanumeric characters
    # and underscores and cannot start with a digit.
    pattern = re.compile(r"\W|^(?=\d)", re.ASCII)
    if not name.isidentifier():
        name = re.sub(pattern, "_", name)

    # Convert to snake case
    name = re.sub("((?<=[a-z0-9])[A-Z]|(?!^)(?<!_)[A-Z](?=[a-z]))", r"_\1", name).lower()

    while keyword.iskeyword(name):
        name += "_"

    return name


def setup_logger(logger: logging.Logger) -> None:
    """Setup the logger for the runtime modules with the appropriate level.

    It involves:
        * Use the `QISKIT_IBM_RUNTIME_LOG_LEVEL` environment variable to
          determine the log level to use for the runtime modules. If an invalid
          level is set, the log level defaults to ``WARNING``. The valid log levels
          are ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``
          (case-insensitive). If the environment variable is not set, then the parent
          logger's level is used, which also defaults to `WARNING`.
        * Use the `QISKIT_IBM_RUNTIME_LOG_FILE` environment variable to specify the
          filename to use when logging messages. If a log file is specified, the log
          messages will not be logged to the screen. If a log file is not specified,
          the log messages will only be logged to the screen and not to a file.
    """
    log_level = os.getenv("QISKIT_IBM_RUNTIME_LOG_LEVEL", "")
    log_file = os.getenv("QISKIT_IBM_RUNTIME_LOG_FILE", "")

    # Setup the formatter for the log messages.
    log_fmt = "%(module)s.%(funcName)s:%(levelname)s:%(asctime)s: %(message)s"
    formatter = logging.Formatter(log_fmt)

    # Set propagate to `False` since handlers are to be attached.
    logger.propagate = False

    # Log messages to a file (if specified), otherwise log to the screen (default).
    if log_file:
        # Setup the file handler.
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # Setup the stream handler, for logging to console, with the given format.
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # Set the logging level after formatting, if specified.
    if log_level:
        # Default to `WARNING` if the specified level is not valid.
        level = logging.getLevelName(log_level.upper())
        if not isinstance(level, int):
            logger.warning(
                '"%s" is not a valid log level. The valid log levels are: '
                "`DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.",
                log_level,
            )
            level = logging.WARNING
        logger.debug('The logger is being set to level "%s"', level)
        logger.setLevel(level)


def filter_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return the data with certain fields filtered.

    Data to be filtered out includes hub/group/project information.

    Args:
        data: Original data to be filtered.

    Returns:
        Filtered data.
    """
    if not isinstance(data, dict):
        return data

    data_to_filter = copy.deepcopy(data)
    keys_to_filter = ["hubInfo"]
    _filter_value(data_to_filter, keys_to_filter)  # type: ignore[arg-type]
    return data_to_filter


def _filter_value(data: Dict[str, Any], filter_keys: List[Union[str, Tuple[str, str]]]) -> None:
    """Recursive function to filter out the values of the input keys.

    Args:
        data: Data to be filtered
        filter_keys: A list of keys whose values are to be filtered out. Each
            item in the list can be a string or a tuple. A tuple indicates nested
            keys, such as ``{'backend': {'name': ...}}`` and must have a length
            of 2.
    """
    for key, value in data.items():
        for filter_key in filter_keys:
            if isinstance(filter_key, str) and key == filter_key:
                data[key] = "..."
            elif key == filter_key[0] and filter_key[1] in value:
                data[filter_key[0]][filter_key[1]] = "..."
            elif isinstance(value, dict):
                _filter_value(value, filter_keys)


class RefreshQueue(Queue):
    """A queue that replaces the oldest item with the new item being added when full.

    A FIFO queue with a bounded size. Once the queue is full, when a new item
    is being added, the oldest item on the queue is discarded to make space for
    the new item.
    """

    def __init__(self, maxsize: int):
        """RefreshQueue constructor.

        Args:
            maxsize: Maximum size of the queue.
        """
        self.condition = Condition()
        super().__init__(maxsize=maxsize)

    def put(self, item: Any) -> None:  # type: ignore[override]
        """Put `item` into the queue.

        If the queue is full, the oldest item is replaced by `item`.

        Args:
            item: Item to put into the queue.
        """
        # pylint: disable=arguments-differ

        with self.condition:
            if self.full():
                super().get(block=False)
            super().put(item, block=False)
            self.condition.notify()

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """Remove and return an item from the queue.

        Args:
            block: If ``True``, block if necessary until an item is available.
            timeout: Block at most `timeout` seconds before raising the
                ``queue.Empty`` exception if no item was available. If
                ``None``, block indefinitely until an item is available.

        Returns:
            An item from the queue.

        Raises:
            queue.Empty: If `block` is ``False`` and no item is available, or
                if `block` is ``True`` and no item is available before `timeout`
                is reached.
        """
        with self.condition:
            if block and self.empty():
                self.condition.wait(timeout)
            return super().get(block=False)

    def notify_all(self) -> None:
        """Wake up all threads waiting for items on the queued."""
        with self.condition:
            self.condition.notify_all()


class CallableStr(str):
    """A callable string."""

    def __call__(self) -> str:
        return self
