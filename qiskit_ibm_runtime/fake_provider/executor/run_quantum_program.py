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
from typing import TYPE_CHECKING

import numpy as np
from qiskit.primitives.containers.bindings_array import BindingsArray
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler import PassManager
from qiskit.utils.optionals import HAS_AER
from samplomatic import Tag, Twirl
from samplomatic.annotations import ChangeBasis, DressingMode, InjectLocalClifford
from samplomatic.quantum_program import CircuitItem, SamplexItem
from samplomatic.utils import get_annotation

from ...options_models.simulator import BARRIER_POSITIONS
from ...results import QuantumProgramItemResult, QuantumProgramResult
from .broadcast_sample import broadcast_sample
from .insert_noise_pass import InsertNoisePass

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.circuit import CircuitInstruction
    from qiskit.providers import BackendV2
    from qiskit.quantum_info import PauliLindbladMap

    from ...options_models.simulator import PositionedLayerNoiseModel, SimulatorOptions
    from ...quantum_program import QuantumProgram

if HAS_AER:
    from qiskit_aer import AerSimulator
    from qiskit_aer.primitives import SamplerV2 as AerSamplerV2


#: The position used for an entry that does not name one, chosen to match the historical behaviour
#: of inserting every channel after the layer body.
DEFAULT_NOISE_POSITION = "R"

#: Which barrier a body-relative position resolves to, per dressing.  A left-dressed layer flattens
#: to ``L | dressing | M | body | R`` and a right-dressed one to ``L | body | M | dressing | R``, so
#: the barrier that sits against the body depends on which side the dressing is anchored to.
_BODY_POSITION_TO_BARRIER = {
    ("before", DressingMode.LEFT): "M",
    ("after", DressingMode.LEFT): "R",
    ("before", DressingMode.RIGHT): "L",
    ("after", DressingMode.RIGHT): "M",
}

#: Annotations that can anchor a layer's dressing to one side.  Any one of them fixes the dressing,
#: and ``get_annotation`` returns whichever appears on the box first.
_DRESSING_ANNOTATIONS = (Twirl, ChangeBasis, InjectLocalClifford)


def _resolve_position(instruction: CircuitInstruction, position: str) -> str:
    """Resolve a noise position to the barrier the noise is inserted after.

    Args:
        instruction: The boxed layer the noise belongs to.
        position: A barrier name, which is returned as-is, or a body-relative name.

    Returns:
        One of ``"L"``, ``"M"`` or ``"R"``.
    """
    if position in BARRIER_POSITIONS:
        return position

    # A dressing annotation does not always survive to here: `find_unique_box_instructions` keeps
    # only Tag, Twirl and InjectNoise, so a layer dressed by ChangeBasis or InjectLocalClifford
    # alone arrives with no dressing at all. Left is both samplomatic's default and the only
    # dressing that builds without a preceding collector.
    dressing = DressingMode.LEFT
    if (annotation := get_annotation(instruction.operation, _DRESSING_ANNOTATIONS)) is not None:
        dressing = annotation.dressing

    return _BODY_POSITION_TO_BARRIER[(position, dressing)]


def _build_noise_dict(
    layer_noise_model: Sequence[PositionedLayerNoiseModel],
) -> dict[str, dict[str, PauliLindbladMap]]:
    """Resolve a layer noise model into the per-tag, per-position form the noise pass takes.

    Entries whose box carries no :class:`~samplomatic.Tag` are skipped: the tag is what ties the
    box to a barrier in the flattened template circuit, so without one there is nothing to match.

    Args:
        layer_noise_model: The entries to resolve.

    Returns:
        A map from tag to a map from noise position to noise.

    Raises:
        ValueError: If two entries place noise at the same position of the same layer.
    """
    noise_dict: dict[str, dict[str, PauliLindbladMap]] = {}

    for entry in layer_noise_model:
        instruction, pauli_map = entry[0], entry[1]
        if (tag := get_annotation(instruction.operation, Tag)) is None:
            continue

        position = _resolve_position(
            instruction, entry[2] if len(entry) == 3 else DEFAULT_NOISE_POSITION
        )
        by_position = noise_dict.setdefault(tag.ref, {})
        if position in by_position:
            raise ValueError(
                f"Found two entries in 'layer_noise_model' placing noise at position "
                f"{position!r} of the same layer. Each position of a layer takes one noise map."
            )
        by_position[position] = pauli_map

    return noise_dict


def _round_to_clifford(values: np.ndarray, decimals: int) -> np.ndarray:
    """Round angles to the nearest multiple of π/2 at ``decimals`` decimal places.

    This prevents floating-point drift from disqualifying nominally-Clifford circuits
    from the stabilizer simulation method.
    """
    return np.round(values / (np.pi / 2), decimals=decimals) * (np.pi / 2)


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

    noise_dict: dict[str, dict[str, PauliLindbladMap]] = {}
    if layer_noise_model := options.layer_noise_model:
        noise_dict = _build_noise_dict(layer_noise_model)

    result_list = []
    for prog_item in program.items:
        if noise_dict:
            circuit = PassManager([InsertNoisePass(noise_dict=noise_dict)]).run(prog_item.circuit)
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
