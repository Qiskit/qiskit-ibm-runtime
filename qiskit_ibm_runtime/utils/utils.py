# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
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

import logging
import os
from itertools import chain
from typing import TYPE_CHECKING

import numpy as np
from qiskit.circuit import ControlFlowOp, ParameterExpression
from qiskit.circuit.delay import Delay
from qiskit.circuit.library.standard_gates import (
    PhaseGate,
    RZGate,
    U1Gate,
)
from qiskit.qpy import QPY_VERSION
from samplomatic.ssv import SSV

if TYPE_CHECKING:
    from qiskit.circuit import Parameter, QuantumCircuit
    from qiskit.circuit.gate import Instruction
    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from qiskit.primitives.containers.sampler_pub import SamplerPub
    from qiskit.providers.backend import BackendV2
    from qiskit.transpiler import Target


def get_ssv_version(highest_value: int | None = None) -> int:
    """Returns the largest SSV available with the installed version of Samplomatic.

    Args:
        highest_value: If it would return an ssv version larger than `highest_value`, return
            `highest_value` instead.
    """
    if highest_value is None:
        return SSV
    return SSV if SSV <= highest_value else highest_value


def get_qpy_version(highest_value: int | None = None) -> int:
    """Returns the largest qpy version available with the installed version of Qiskit.

    Args:
        highest_value: If it would return a qpy version larger than `highest_value`, return
            `highest_value` instead.
    """
    if highest_value is None:
        return QPY_VERSION
    return QPY_VERSION if QPY_VERSION <= highest_value else highest_value


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


def _is_isa_circuit_helper(circuit: QuantumCircuit, target: Target, qubit_map: dict) -> str:
    """Helper for checking if a circuit is an ISA circuit.

    A section of is_isa_circuit, separated to allow recursive calls within blocks of conditional
    operations.
    """
    for instruction in circuit.data:
        operation = instruction.operation

        name = operation.name
        qargs = tuple(qubit_map[bit] for bit in instruction.qubits)
        if not target.instruction_supported(name, qargs) and name not in {"barrier", "store"}:
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
    """Checks if the circuit is an ISA circuit.

    An ISA circuit means that it has a layout and that it only uses instructions that exist in the
    target.

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


def _is_valid_rzz_pub_helper(circuit: QuantumCircuit) -> str | set[Parameter]:
    """Helper for validating ``rzz`` gates in pubs.

    For rzz gates:
    - Verify that numeric angles are in the range [0, pi/2]
    - Collect parameterized angles.

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


def is_valid_rzz_pub(pub: EstimatorPub | SamplerPub) -> str:
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


def are_circuits_dynamic(circuits: list[QuantumCircuit], qasm_default: bool = True) -> bool:
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
    """Test if a gate is considered fractional by IBM.

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


def is_crn(locator: str) -> bool:
    """Check if a given value is a CRN (Cloud Resource Name).

    Args:
        locator: The value to check.

    Returns:
        Whether the input is a CRN.
    """
    return isinstance(locator, str) and locator.startswith("crn:")


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
