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

"""Simulator options for executor-based primitives."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, TypeAlias

from pydantic import AfterValidator, InstanceOf
from qiskit.circuit import BoxOp, CircuitInstruction
from qiskit.quantum_info import PauliLindbladMap

from .base import BaseOptionsModel

if TYPE_CHECKING:
    from qiskit.circuit import QuantumCircuit


def validate_layer_noise_model(value: LayerNoiseModel | None) -> LayerNoiseModel | None:
    """Validate the ``LayerNoiseModel``."""
    if value:
        instruction, noise = value
        if not isinstance(instruction.operation, BoxOp):
            raise ValueError("Found an instruction that does not contain a box.")
        if len(instruction.qubits) != noise.num_qubits:
            raise ValueError(
                f"Found instruction with {len(instruction.qubits)}"
                f"qubits but a noise model with {noise.num_qubits}."
            )
    return value


LayerNoiseModel: TypeAlias = Annotated[
    tuple[Annotated[CircuitInstruction, InstanceOf], Annotated[PauliLindbladMap, InstanceOf]],
    AfterValidator(validate_layer_noise_model),
]

BARRIER_POSITIONS = ("L", "M", "R")
"""Noise positions naming one of the three barriers samplomatic emits around a layer."""

BODY_POSITIONS = ("before", "after")
"""Noise positions naming a side of a layer's body, resolved against the layer's dressing."""

NOISE_POSITIONS = (*BARRIER_POSITIONS, *BODY_POSITIONS)
"""The positions at which a layer's noise may be placed."""


def body_is_absorbed_into_dressing(body: QuantumCircuit) -> bool:
    """Return whether every operation in a layer's body is absorbed into its dressing.

    Samplomatic pushes single-qubit gates out of a box body and into the dressing, so a body holding
    nothing else is equivalent to an empty one: the barriers on either side of it end up adjacent.

    Args:
        body: The body of a boxed layer.
    """
    # `measure` and `reset` are single-qubit but are not standard gates, so they are not absorbed.
    return all(
        instruction.is_standard_gate() and instruction.operation.num_qubits == 1
        for instruction in body.data
    )


def validate_positioned_layer_noise_model(
    value: PositionedLayerNoiseModel,
) -> PositionedLayerNoiseModel:
    """Validate a ``LayerNoiseModel`` entry that may carry a noise position."""
    validate_layer_noise_model(value[:2])  # type: ignore[arg-type]

    if len(value) == 3:
        position = value[2]
        if position not in NOISE_POSITIONS:
            raise ValueError(
                f"Found the noise position {position!r}, but expected one of "
                f"{list(NOISE_POSITIONS)}."
            )
        if position in BODY_POSITIONS and body_is_absorbed_into_dressing(value[0].operation.body):
            raise ValueError(
                f"The noise position {position!r} is ambiguous for a layer whose body holds "
                f"nothing but single-qubit gates: those gates are absorbed into the layer's "
                f"dressing, leaving 'before' and 'after' naming the same point. Name a barrier "
                f"explicitly, one of {list(BARRIER_POSITIONS)}, instead."
            )

    return value


PositionedLayerNoiseModel: TypeAlias = Annotated[
    tuple[Annotated[CircuitInstruction, InstanceOf], Annotated[PauliLindbladMap, InstanceOf]]
    | tuple[
        Annotated[CircuitInstruction, InstanceOf],
        Annotated[PauliLindbladMap, InstanceOf],
        str,
    ],
    AfterValidator(validate_positioned_layer_noise_model),
]


class SimulatorOptions(BaseOptionsModel):
    """Simulator options."""

    angle_decimals: int = 5
    """Gate angle decimal precision.

    Gate angles are rounded to the nearest multiple of ``np.pi/2`` at this decimal precision before
    simulation. This prevents floating-point drift from preventing Clifford-method simulation when
    angles are nominally Clifford.
    """

    layer_noise_model: list[PositionedLayerNoiseModel] | None = None
    """Noise model specified by a collection of instructions and the noise that affects them.

    Each entry is a ``(instruction, noise)`` pair, or a ``(instruction, noise, position)`` triple
    where ``position`` is one of :data:`NOISE_POSITIONS` and says where in the layer the noise acts.
    An entry that omits the position has one derived from what its layer's body does: a layer that
    measures gets ``"before"``, and every other layer gets ``"after"``.

    A position is either body-relative, ``"before"`` or ``"after"`` the layer's body, or one of the
    barriers ``"L"``, ``"M"`` and ``"R"`` that samplomatic emits around the layer.

    .. note::
        A body-relative position is relative to the layer's body *after dressing*, which is not
        always the body as written.  Single-qubit gates are moved out of a body and into the
        dressing — those leading it under left dressing, those trailing it under right dressing — so
        for a left-dressed layer holding ``x(0); cz(0, 1)`` the ``x`` becomes dressing, and
        ``"before"`` places the noise *after* the ``x`` rather than before it.

        An error is raised if ``"before"`` or ``"after"`` is used for a layer whose body holds
        nothing but single-qubit gates.

    When simulating an estimator job, if this value is set to ``None``,
    it defaults to the value of
    :attr:`qiskit_ibm_runtime.options_models.ResilienceOptions.layer_noise_model`.
    """

    seed_simulator: int | None = None
    """Random seed to control sampling."""

    warn_absent: bool = True
    """Whether to emit a warning when an entry is missing in :attr:`layer_noise_dict`."""
