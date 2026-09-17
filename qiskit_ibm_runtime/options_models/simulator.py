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

from typing import Annotated, TypeAlias

from pydantic import AfterValidator, InstanceOf
from qiskit.circuit import BoxOp, CircuitInstruction
from qiskit.quantum_info import PauliLindbladMap

from .base import BaseOptionsModel


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

NOISE_POSITIONS = ("L", "M", "R")
"""The positions at which a layer's noise may be placed."""


def validate_positioned_layer_noise_model(
    value: PositionedLayerNoiseModel,
) -> PositionedLayerNoiseModel:
    """Validate a ``LayerNoiseModel`` entry that may carry a noise position."""
    validate_layer_noise_model(value[:2])  # type: ignore[arg-type]

    if len(value) == 3 and (position := value[2]) not in NOISE_POSITIONS:
        raise ValueError(
            f"Found the noise position {position!r}, but expected one of {list(NOISE_POSITIONS)}."
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
    where ``position`` is one of :data:`NOISE_POSITIONS` and says where in the layer the noise
    acts.  An entry that omits the position defaults to ``"R"``, after the layer's body.

    When simulating an estimator job, if this value is set to ``None``,
    it defaults to the value of
    :attr:`qiskit_ibm_runtime.options_models.ResilienceOptions.layer_noise_model`.
    """

    seed_simulator: int | None = None
    """Random seed to control sampling."""

    warn_absent: bool = True
    """Whether to emit a warning when an entry is missing in :attr:`layer_noise_dict`."""
