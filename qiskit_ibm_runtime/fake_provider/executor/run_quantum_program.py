# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Functions for running a QuantumProgram on a local Aer simulator."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Literal, TypeAlias

import numpy as np
from qiskit.primitives.containers.bindings_array import BindingsArray
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler import PassManager
from qiskit.utils.optionals import HAS_AER
from samplomatic import Tag, Twirl
from samplomatic.quantum_program import CircuitItem, SamplexItem
from samplomatic.utils import get_annotation, undress_box

from ...exceptions import IBMInputValueError
from ...results import QuantumProgramItemResult, QuantumProgramResult
from .broadcast_sample import broadcast_sample
from .insert_noise_pass import InsertNoisePass

if TYPE_CHECKING:
    from qiskit.circuit import CircuitInstruction
    from qiskit.providers import BackendV2

    from ...options_models.simulator import SimulatorOptions
    from ...quantum_program import QuantumProgram

if HAS_AER:
    from qiskit_aer import AerSimulator
    from qiskit_aer.primitives import SamplerV2 as AerSamplerV2

# TypeAlias for a BoxOp type
BoxType: TypeAlias = Literal["gates", "measurement", "unknown"]


def _round_to_clifford(values: np.ndarray, decimals: int) -> np.ndarray:
    """Round angles to the nearest multiple of π/2 at ``decimals`` decimal places.

    This prevents floating-point drift from disqualifying nominally-Clifford circuits
    from the stabilizer simulation method.
    """
    return np.round(values / (np.pi / 2), decimals=decimals) * (np.pi / 2)


def find_box_type(instruction: CircuitInstruction) -> BoxType:
    """Find the type of :class:`~qiskit.circuit.BoxOp` that ``instruction`` contains.

    Args:
        instruction: The instruction to get the type of.

    Returns:
        The box type. Can be one of ``"gates"``, ``"measurement"``, or ``"unknown"``.

    Raises:
        IBMInputValueError: If ``instruction`` does not contain a box.
    """
    box = instruction.operation
    if (name := box.name) != "box":
        raise IBMInputValueError(f"Expected a 'box' but found '{name}'.")

    undressed_box = undress_box(box)

    if len(undressed_box.body) == 0:
        return "gates"

    all_gates = all(op.is_standard_gate() or op.name == "barrier" for op in undressed_box.body)
    all_measurement = all(op.name in ["measure", "barrier"] for op in undressed_box.body)

    if all_gates and not all_measurement:
        return "gates"
    elif not all_gates and all_measurement:
        return "measurement"

    return "unknown"


def determine_barrier_position(layer: CircuitInstruction) -> Literal["L", "M", "R"]:
    """Determines the barrier position to inject noise based on the box type and dressing.

    Args:
        layer: The layer to evaluate.

    Returns:
        The barrier position to inject the noise into.

    Raises:
        TypeError: If ``layer`` is an "unknown" box type.
    """
    box_type = find_box_type(layer)

    if box_type == "unknown":
        raise TypeError(f"Unsupported box type: {box_type}")

    if box_type == "measurement":
        return "M"

    if box_type == "gates" and (twirl := get_annotation(layer.operation, Twirl)) is not None:
        if twirl.dressing.value == "right":
            return "L"

    return "R"


@HAS_AER.require_in_call
def run_quantum_program(
    backend: BackendV2,
    program: QuantumProgram,
    options: SimulatorOptions,
) -> QuantumProgramResult:
    """Run a quantum program on a simulator.

    Args:
        backend: The backend to simulate.
        program: The program to run.
        options: The simulator options to use.

    Returns:
        Results of simulation.
    """
    seed = options.seed_simulator

    # Generate a sampler
    if isinstance(backend, AerSimulator):
        backend = deepcopy(backend)
        backend.set_max_qubits(10000)
        backend.set_options(seed_simulator=seed)

    aer_sampler = AerSamplerV2.from_backend(backend, seed=seed)

    rng = np.random.default_rng(seed)

    noise_dict = {}
    noise_pos = {}
    if layer_noise_model := options.layer_noise_model:
        for instr, pauli_map in layer_noise_model:
            if annotation := get_annotation(instr.operation, Tag):
                noise_dict[annotation.ref] = pauli_map
                noise_pos[annotation.ref] = determine_barrier_position(instr)

    result_list = []
    for prog_item in program.items:
        if noise_dict:
            circuit = PassManager(
                [
                    InsertNoisePass(
                        noise_dict=noise_dict,
                        noise_pos=noise_pos,
                        warn_absent=options.warn_absent,
                    )
                ]
            ).run(prog_item.circuit)
        else:
            circuit = prog_item.circuit

        if isinstance(prog_item, CircuitItem):
            if prog_item.circuit_arguments is not None:
                bindings_array = BindingsArray(
                    {tuple(prog_item.circuit.parameters): prog_item.circuit_arguments}
                )
                for k, v in bindings_array._data.items():
                    bindings_array._data[k] = _round_to_clifford(v, options.angle_decimals)
            else:
                bindings_array = None
            sampler_res = aer_sampler.run(
                [
                    SamplerPub(
                        circuit=circuit,
                        parameter_values=bindings_array,
                        shots=program.shots,
                    )  # type: ignore
                ]
            ).result()
            bit_array = sampler_res[0].data
            data = {key: ba.to_bool_array(order="little") for key, ba in dict(bit_array).items()}
            result_list.append(
                QuantumProgramItemResult(result=data, metadata=sampler_res[0].metadata)
            )

        elif isinstance(prog_item, SamplexItem):
            samplex_data = broadcast_sample(
                prog_item.samplex,
                prog_item.samplex_arguments,
                prog_item.shape,
                rng,
            )
            bindings_array = BindingsArray(
                {tuple(prog_item.circuit.parameters): samplex_data.pop("parameter_values")}
            )
            for k, v in bindings_array._data.items():
                bindings_array._data[k] = _round_to_clifford(v, options.angle_decimals)
            sampler_res = aer_sampler.run(
                [
                    SamplerPub(
                        circuit=circuit,
                        parameter_values=bindings_array,
                        shots=program.shots,
                    )  # type: ignore
                ]
            ).result()
            bit_array = sampler_res[0].data
            bool_arrays = {
                key: ba.to_bool_array(order="little") for key, ba in dict(bit_array).items()
            }
            data = {**samplex_data, **bool_arrays}
            result_list.append(
                QuantumProgramItemResult(result=data, metadata=sampler_res[0].metadata)
            )

        else:
            raise TypeError(f"Unsupported QuantumProgramItem type: {type(prog_item)}")

    ret = QuantumProgramResult(
        data=result_list,
        metadata=None,
        passthrough_data=program.passthrough_data,
    )
    ret._semantic_role = program._semantic_role
    return ret
