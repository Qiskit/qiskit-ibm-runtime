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
from typing import Any, Dict, List

from qiskit.circuit.controlflow import (
    CONTROL_FLOW_OP_NAMES,
    ForLoopOp,
    IfElseOp,
    SwitchCaseOp,
    WhileLoopOp,
)
from qiskit.circuit.gate import Gate
from qiskit.circuit.library.standard_gates import get_standard_gate_name_mapping
from qiskit.circuit.parameter import Parameter
from qiskit.providers.backend import QubitProperties
from qiskit.transpiler.target import InstructionProperties, Target

from ..models import BackendConfiguration, BackendProperties
from ..models.exceptions import BackendPropertyError

# is_fractional_gate used to be defined in this module and might be referenced
# from here externally
from .utils import is_fractional_gate  # See comment above before removing


logger = logging.getLogger(__name__)


def convert_to_target(  # type: ignore[no-untyped-def]
    configuration: BackendConfiguration,
    properties: BackendProperties = None,
    *,
    include_control_flow: bool = True,
    include_fractional_gates: bool = True,
    **kwargs,
) -> Target:
    """Decode transpiler target from backend data set.

    This function generates :class:`.Target`` instance from intermediate
    legacy objects such as :class:`.BackendProperties` and :class:`.BackendConfiguration`.

    Args:
        configuration: Backend configuration as ``BackendConfiguration``
        properties: Backend property dictionary or ``BackendProperties``
        include_control_flow: Set True to include control flow instructions.
        include_fractional_gates: Set True to include fractioanl gates.

    Returns:
        A ``Target`` instance.
    """
    add_delay = True
    filter_faulty = True

    if "defaults" in kwargs:
        warnings.warn(
            "Backend defaults have been completely from removed IBM Backends. They will be ignored."
        )

    required = ["measure", "delay", "reset"]

    # Load Qiskit object representation
    qiskit_inst_mapping = get_standard_gate_name_mapping()

    qiskit_control_flow_mapping = {
        "if_else": IfElseOp,
        "while_loop": WhileLoopOp,
        "for_loop": ForLoopOp,
        "switch_case": SwitchCaseOp,
    }

    in_data = {"num_qubits": configuration.n_qubits}

    # Parse global configuration properties
    if hasattr(configuration, "dt"):
        in_data["dt"] = configuration.dt  # type: ignore[assignment]
    if hasattr(configuration, "timing_constraints"):
        in_data.update(configuration.timing_constraints)

    # Create instruction property placeholder from backend configuration
    basis_gates = set(getattr(configuration, "basis_gates", []))
    supported_instructions = set(getattr(configuration, "supported_instructions", []))
    gate_configs = {gate.name: gate for gate in configuration.gates}
    all_instructions = set.union(
        basis_gates, set(required), supported_instructions.intersection(CONTROL_FLOW_OP_NAMES)
    )

    inst_name_map = {}

    faulty_ops = set()
    faulty_qubits = set()
    unsupported_instructions = []

    # Create name to Qiskit instruction object repr mapping
    for name in all_instructions:
        if name in qiskit_control_flow_mapping:
            if not include_control_flow:
                # Remove name if this is control flow and dynamic circuits feature is disabled.
                logger.info(
                    "Control flow %s is found but the dynamic circuits are disabled for this backend. "
                    "This instruction is excluded from the backend Target.",
                    name,
                )
                unsupported_instructions.append(name)
            continue
        if name in qiskit_inst_mapping:
            qiskit_gate = qiskit_inst_mapping[name]
            if (not include_fractional_gates) and is_fractional_gate(qiskit_gate):
                # Remove name if this is fractional gate and fractional gate feature is disabled.
                logger.info(
                    "Gate %s is found but the fractional gates are disabled for this backend. "
                    "This gate is excluded from the backend Target.",
                    name,
                )
                unsupported_instructions.append(name)
                continue
            inst_name_map[name] = qiskit_gate
        elif name in gate_configs:
            # GateConfig model is a translator of QASM opcode.
            # This doesn't have quantum definition, so Qiskit transpiler doesn't perform
            # any optimization in quantum domain.
            # Usually GateConfig counterpart should exist in Qiskit namespace so this is rarely called.
            this_config = gate_configs[name]
            params = list(map(Parameter, getattr(this_config, "parameters", [])))
            coupling_map = getattr(this_config, "coupling_map", [])
            inst_name_map[name] = Gate(
                name=name,
                num_qubits=len(coupling_map[0]) if coupling_map else 0,
                params=params,
            )
        else:
            warnings.warn(
                f"No gate definition for {name} can be found and is being excluded "
                "from the generated target. You can use `custom_name_mapping` to provide "
                "a definition for this operation.",
                RuntimeWarning,
            )
            unsupported_instructions.append(name)

    for name in unsupported_instructions:
        all_instructions.remove(name)

    # Create inst properties placeholder
    # Without any assignment, properties value is None,
    # which defines a global instruction that can be applied to any qubit(s).
    # The None value behaves differently from an empty dictionary.
    # See API doc of Target.add_instruction for details.
    prop_name_map = dict.fromkeys(all_instructions)
    for name in all_instructions:
        if name in gate_configs:
            if coupling_map := getattr(gate_configs[name], "coupling_map", None):
                # Respect operational qubits that gate configuration defines
                # This ties instruction to particular qubits even without properties information.
                # Note that each instruction is considered to be ideal unless
                # its spec (e.g. error, duration) is bound by the properties object.
                prop_name_map[name] = dict.fromkeys(map(tuple, coupling_map))

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
                    t1=prop_dict.get("T1", (None, None))[0],  # type: ignore[arg-type, union-attr]
                    t2=prop_dict.get("T2", (None, None))[0],  # type: ignore[arg-type, union-attr]
                    frequency=prop_dict.get(  # type: ignore[arg-type, union-attr]
                        "frequency", (None, None)
                    )[0],
                )
            )
        in_data["qubit_properties"] = qubit_properties  # type: ignore[assignment]

        for name in all_instructions:
            try:
                for qubits, param_dict in properties.gate_property(
                    name
                ).items():  # type: ignore[arg-type, union-attr]
                    if filter_faulty and (
                        set.intersection(faulty_qubits, qubits)
                        or not properties.is_gate_operational(name, qubits)
                    ):
                        try:
                            # Qubits might be pre-defined by the gate config
                            # However properties objects says the qubits is non-operational
                            del prop_name_map[name][qubits]
                        except KeyError:
                            pass
                        faulty_ops.add((name, qubits))
                        continue
                    if prop_name_map[name] is None:
                        # This instruction is tied to particular qubits
                        # i.e. gate config is not provided, and instruction has been globally defined.
                        prop_name_map[name] = {}
                    prop_name_map[name][qubits] = InstructionProperties(
                        error=_get_value(param_dict, "gate_error"),  # type: ignore[arg-type]
                        duration=_get_value(param_dict, "gate_length"),  # type: ignore[arg-type]
                    )
                if isinstance(prop_name_map[name], dict) and any(
                    v is None for v in prop_name_map[name].values()
                ):
                    # Properties provides gate properties only for subset of qubits
                    # Associated qubit set might be defined by the gate config here
                    logger.info(
                        "Gate properties of instruction %s are not provided for every qubits. "
                        "This gate is ideal for some qubits and the rest is with finite error. "
                        "Created backend target may confuse error-aware circuit optimization.",
                        name,
                    )
            except BackendPropertyError:
                # This gate doesn't report any property
                continue

        # Measure instruction property is stored in qubit property
        prop_name_map["measure"] = {}

        for qubit_idx in range(configuration.num_qubits):
            if filter_faulty and (qubit_idx in faulty_qubits):
                continue
            qubit_prop = properties.qubit_property(qubit_idx)
            prop_name_map["measure"][(qubit_idx,)] = InstructionProperties(
                error=_get_value(qubit_prop, "readout_error"),  # type: ignore[arg-type]
                duration=_get_value(qubit_prop, "readout_length"),  # type: ignore[arg-type]
            )

    for op in required:
        # Map required ops to each operational qubit
        if prop_name_map[op] is None:
            prop_name_map[op] = {
                (q,): None
                for q in range(configuration.num_qubits)
                if not filter_faulty or (q not in faulty_qubits)
            }

    # Add parsed properties to target
    target = Target(**in_data)
    for inst_name in all_instructions:
        if inst_name == "delay" and not add_delay:
            continue
        if inst_name in qiskit_control_flow_mapping:
            # Control flow operator doesn't have gate property.
            target.add_instruction(
                instruction=qiskit_control_flow_mapping[inst_name],
                name=inst_name,
            )
        else:
            target.add_instruction(
                instruction=inst_name_map[inst_name],
                properties=prop_name_map.get(inst_name, None),
                name=inst_name,
            )
    return target


def qubit_props_list_from_props(
    properties: BackendProperties,
) -> List[QubitProperties]:
    """Uses BackendProperties to construct
    and return a list of QubitProperties.
    """
    qubit_props: List[QubitProperties] = []
    for qubit, _ in enumerate(properties.qubits):
        try:
            t_1 = properties.t1(qubit)
        except BackendPropertyError:
            t_1 = None
        try:
            t_2 = properties.t2(qubit)
        except BackendPropertyError:
            t_2 = None
        try:
            frequency = properties.frequency(qubit)
        except BackendPropertyError:
            frequency = None
        qubit_props.append(
            QubitProperties(  # type: ignore[no-untyped-call]
                t1=t_1,
                t2=t_2,
                frequency=frequency,
            )
        )
    return qubit_props
