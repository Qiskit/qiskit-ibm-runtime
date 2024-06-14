# This code is part of Qiskit.
#
# (C) Copyright IBM 2022, 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Converters for migration from IBM Quantum BackendV1 to BackendV2."""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from typing import Any, Dict, Type
from collections import defaultdict

from qiskit.circuit.controlflow import (
    CONTROL_FLOW_OP_NAMES,
    ForLoopOp,
    IfElseOp,
    SwitchCaseOp,
    WhileLoopOp,
)
from qiskit.circuit.gate import Gate
from qiskit.circuit.library.standard_gates import (
    get_standard_gate_name_mapping,
    RZGate,
    U1Gate,
    PhaseGate,
)
from qiskit.circuit.instruction import Instruction
from qiskit.circuit.delay import Delay
from qiskit.providers.backend import QubitProperties
from qiskit.providers.exceptions import BackendPropertyError
from qiskit.providers.models.backendproperties import BackendProperties
from qiskit.providers.models.pulsedefaults import PulseDefaults
from qiskit.transpiler.target import InstructionProperties, Target

from qiskit_ibm_runtime.models.backend_configuration import IBMBackendConfiguration

logger = logging.getLogger(__name__)


@dataclass
class InstructionEntry:
    """A collection of information to populate Qiskit target"""

    qiskit_instruction: Instruction | Type[Instruction]
    properties: dict[tuple[int, ...], InstructionProperties] | None = None
    name: str | None = None


def convert_to_target(
    configuration: IBMBackendConfiguration,
    properties: BackendProperties = None,
    defaults: PulseDefaults = None,
    *,
    include_control_flow: bool = True,
    include_fractional_gates: bool = True,
) -> Target:
    """Decode transpiler target from backend data set.

    This function generates :class:`.Target`` instance from intermediate
    legacy objects such as :class:`.BackendProperties` and :class:`.PulseDefaults`.
    These objects are usually components of the legacy :class:`.BackendV1` model.

    Args:
        configuration: Backend configuration as ``IBMBackendConfiguration``
        properties: Backend property dictionary or ``BackendProperties``
        defaults: Backend pulse defaults dictionary or ``PulseDefaults``
        include_control_flow: Set True to include control flow instructions.
        include_fractional_gates: Set True to include fractioanl gates.

    Returns:
        A ``Target`` instance.
    """
    required = ["measure", "delay", "reset"]

    # Load Qiskit object representation
    qiskit_inst_mapping = get_standard_gate_name_mapping()

    qiskit_control_flow_mapping = {
        "if_else": IfElseOp,
        "while_loop": WhileLoopOp,
        "for_loop": ForLoopOp,
        "switch_case": SwitchCaseOp,
    }

    in_data = {
        "num_qubits": configuration.n_qubits,
        "dt": configuration.dt,
    }
    if configuration.timing_constraints:
        in_data.update(configuration.timing_constraints.model_dump())

    # Create instruction property placeholder from backend configuration
    basis_gates = set(configuration.basis_gates)
    supported_instructions = set(configuration.supported_instructions)
    gate_configs = defaultdict(list)
    for gate in configuration.gates:
        gate_configs[gate.name].append(gate)
    all_instructions = set.union(
        basis_gates, set(required), supported_instructions.intersection(CONTROL_FLOW_OP_NAMES)
    )

    faulty_ops = set()
    faulty_qubits = set()

    entries: list[InstructionEntry] = []
    # Create name to Qiskit instruction object repr mapping
    for name in all_instructions:
        if qiskit_control_flow_op := qiskit_control_flow_mapping.get(name, None):
            if not include_control_flow:
                # Remove name if this is control flow and dynamic circuits feature is disabled.
                logger.info(
                    "Control flow %s is found but the dynamic circuits are disabled for this backend. "
                    "This instruction is excluded from the backend Target.",
                    name,
                )
                continue
            entries.append(
                InstructionEntry(
                    qiskit_instruction=qiskit_control_flow_op,
                    properties=None,
                    name=name,
                )
            )
        elif qiskit_gate := qiskit_inst_mapping.get(name, None):
            # Standard Qiskit gates
            if (not include_fractional_gates) and is_fractional_gate(qiskit_gate):
                # Remove name if this is fractional gate and fractional gate feature is disabled.
                logger.info(
                    "Gate %s is found but the fractional gates are disabled for this backend. "
                    "This gate is excluded from the backend Target.",
                    name,
                )
                continue
            if name in gate_configs:
                # Respect gate configuration from the backend
                for sub_gate in gate_configs[name]:
                    # Respect operational qubits that gate configuration defines
                    # This ties instruction to particular qubits even without properties information.
                    # Note that each instruction is considered to be ideal unless
                    # its spec (e.g. error, duration) is bound by the properties object.
                    entries.append(
                        InstructionEntry(
                            qiskit_instruction=qiskit_gate.base_class(*sub_gate.parameters),
                            properties=dict.fromkeys(sub_gate.coupling_map),
                            name=sub_gate.label or sub_gate.name,
                        )
                    )
            else:
                entries.append(
                    InstructionEntry(
                        qiskit_instruction=qiskit_gate,
                        properties=None,
                        name=qiskit_gate.name,
                    )
                )
        elif name in gate_configs:
            # GateConfig model is a translator of QASM opcode.
            # This doesn't have quantum definition, so Qiskit transpiler doesn't perform
            # any optimization in quantum domain.
            # Usually GateConfig counterpart should exist in Qiskit namespace so this is rarely called.
            for sub_gate in gate_configs[name]:
                opaque_gate = Gate(
                    name=name,
                    num_qubits=len(sub_gate.coupling_map[0]) if sub_gate.coupling_map else 0,
                    params=sub_gate.parameters,
                )
                entries.append(
                    InstructionEntry(
                        qiskit_instruction=opaque_gate,
                        properties=dict.fromkeys(sub_gate.coupling_map),
                        name=sub_gate.label or sub_gate.name,
                    )
                )
        else:
            warnings.warn(
                f"No gate definition for {name} can be found and is being excluded "
                "from the generated target. You can use `custom_name_mapping` to provide "
                "a definition for this operation.",
                RuntimeWarning,
            )

    # Populate instruction properties
    if properties:

        def _get_value(prop_dict: Dict, prop_name: str) -> Any:
            if ndval := prop_dict.get(prop_name, None):
                return ndval[0]
            return None

        # is_qubit_operational is a bit of expensive operation so precache the value
        faulty_qubits = {
            q for q in range(configuration.num_qubits) if not properties.is_qubit_operational(q)
        }

        qubit_properties = []
        for qi in range(0, configuration.num_qubits):
            # TODO faulty qubit handling might be needed since
            #  faulty qubit reporting qubit properties doesn't make sense.
            try:
                prop_dict = properties.qubit_property(qubit=qi)
            except KeyError:
                continue
            qubit_properties.append(
                QubitProperties(
                    t1=prop_dict.get("T1", (None, None))[0],
                    t2=prop_dict.get("T2", (None, None))[0],
                    frequency=prop_dict.get("frequency", (None, None))[0],
                )
            )
        in_data["qubit_properties"] = qubit_properties

        for entry in entries:
            if entry.name in required and entry.properties is None:
                entry.properties = {
                    (q,): None for q in range(configuration.num_qubits) if q not in faulty_qubits
                }
            if entry.name == "measure":
                # Measure instruction property is stored in qubit property
                for qubit_idx in range(configuration.num_qubits):
                    if qubit_idx in faulty_qubits:
                        continue
                    qubit_prop = properties.qubit_property(qubit_idx)
                    entry.properties[(qubit_idx,)] = InstructionProperties(
                        error=_get_value(qubit_prop, "readout_error"),
                        duration=_get_value(qubit_prop, "readout_length"),
                    )
            else:
                try:
                    for qubits, param_dict in properties.gate_property(entry.name).items():
                        if entry.properties is None:
                            # This instruction is tied to particular qubits
                            # i.e. gate config is not provided,
                            # and instruction has been globally defined.
                            entry.properties = {}
                        if set.intersection(
                            faulty_qubits, qubits
                        ) or not properties.is_gate_operational(entry.name, qubits):
                            try:
                                # Qubits might be pre-defined by the gate config
                                # However properties objects says the qubits is non-operational
                                del entry.properties[qubits]
                            except KeyError:
                                pass
                            faulty_ops.add((entry.name, qubits))
                            continue
                        entry.properties[qubits] = InstructionProperties(
                            error=_get_value(param_dict, "gate_error"),
                            duration=_get_value(param_dict, "gate_length"),
                        )
                except BackendPropertyError:
                    # This gate doesn't report any property
                    pass

            if entry.properties is not None and None in entry.properties.values():
                # Properties provides gate properties only for subset of qubits
                # Associated qubit set might be defined by the gate config here
                logger.info(
                    "Gate properties of instruction %s are not provided for every qubits. "
                    "This gate is ideal for some qubits and the rest is with finite error. "
                    "Created backend target may confuse error-aware circuit optimization.",
                    entry.name,
                )

    if defaults:
        inst_sched_map = defaults.instruction_schedule_map

        for entry in entries:
            if entry.properties is None:
                continue
            for qubits, inst_properties in entry.properties.items():
                # We assume calibration is provided with the sub gate name, e.g. rx_30.
                # If we assume parameterized schedule and bind parameter immediately
                # to get sub gate schedule, this causes Qobj parsing overhead.
                # We perfer lazy calibration parsing.
                name_qubits = entry.name, qubits
                if name_qubits in faulty_ops:
                    continue
                if not inst_sched_map.has(*name_qubits):
                    continue
                calibration = inst_sched_map._get_calibration_entry(*name_qubits)
                try:
                    inst_properties.calibration = calibration
                except AttributeError:
                    logger.info(
                        "The PulseDefaults payload received contains an instruction %s on "
                        "qubits %s which is not present in the configuration or properties payload.",
                        *name_qubits,
                    )

    # Add parsed properties to target
    target = Target(**in_data)
    for entry in entries:
        target.add_instruction(
            instruction=entry.qiskit_instruction,
            properties=entry.properties,
            name=entry.name,
        )
    return target


def is_fractional_gate(gate: Gate) -> bool:
    """Test if gate is fractional gate familiy."""
    # In IBM architecture these gates are virtual-Z and delay,
    # which don't change control parameter with its gate parameter.
    exclude_list = (RZGate, PhaseGate, U1Gate, Delay)
    return len(gate.params) > 0 and not isinstance(gate, exclude_list)
