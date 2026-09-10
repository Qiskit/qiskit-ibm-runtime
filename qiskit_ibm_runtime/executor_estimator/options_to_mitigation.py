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

"""Translators from EstimatorOptions to qiskit-mitigation inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction
    from qiskit.quantum_info import PauliLindbladMap

    from ..options_models.twirling import TwirlingOptions


def estimator_options_to_boxing_options(
    twirling_options: TwirlingOptions,
    inject_noise: bool,
    add_tags: bool = False,
) -> dict:
    """Translate twirling options into a ``custom_boxing_options`` dict for qiskit-mitigation.

    This dict is passed directly to ``MitigationTask.prepare()`` (and its subclasses)
    as the ``custom_boxing_options`` argument.

    Noise-injection options (``inject_noise_*``) are **not** set here — ``PEC._box_circuit()``
    and ``PEA._box_circuit()`` enforce their own required values for those fields.

    ``enable_measures`` and ``measure_annotations`` are also **not** set here. When TREX
    is passed to a task, ``trex._edit_boxing_options()`` forces ``enable_measures=True``
    and ``measure_annotations="all"``. When TREX is absent, ``MitigationTask._box_circuit()``
    defaults to ``measure_annotations="change_basis"``, which is correct.

    Args:
        twirling_options: The finalized twirling options.
        inject_noise: Whether noise-injection boxing is requested (PEC/PEA paths).
            When ``True``, ``enable_gates`` is forced on regardless of the twirling setting.
        add_tags: Whether to tag boxes with a hash (``True``) or suppress tags (``False``).
            Used in local/simulator mode for noise injection.

    Returns:
        A dict suitable as ``custom_boxing_options`` for qiskit-mitigation task ``prepare()``.
    """
    return {
        # Gate twirling is on when requested OR when noise injection is needed.
        "enable_gates": twirling_options.enable_gates or inject_noise,
        "twirling_strategy": twirling_options.strategy.replace("-", "_"),
        "twirling_group": twirling_options.group,
        "add_tags": "unique_box" if add_tags else "none",
    }


def layer_noise_model_to_dict(
    layer_noise_model: Iterable[tuple[CircuitInstruction, PauliLindbladMap]],
) -> dict[str, PauliLindbladMap]:
    """Convert a ``layer_noise_model`` iterable to a ``{ref: PauliLindbladMap}`` dict.

    ``EstimatorOptions.resilience.layer_noise_model`` stores pairs of
    ``(CircuitInstruction, PauliLindbladMap)`` where the instruction carries a
    samplomatic ``InjectNoise`` annotation that holds the layer reference string.
    This helper unpacks those annotations into the plain ``ref → map`` dict that
    qiskit-mitigation's ``PEC`` and ``PEA`` task classes expect as ``noise_maps``.

    Args:
        layer_noise_model: Iterable of ``(CircuitInstruction, PauliLindbladMap)`` pairs
            as stored in ``EstimatorOptions.resilience.layer_noise_model``.

    Returns:
        A ``dict`` mapping each layer reference string to its ``PauliLindbladMap``.
        Instructions without an ``InjectNoise`` annotation are silently skipped.
    """
    result: dict[str, PauliLindbladMap] = {}
    for instr, pauli_map in layer_noise_model:
        if annotation := get_annotation(instr.operation, InjectNoise):
            result[annotation.ref] = pauli_map
        # TODO: Refs of tags for simulator?
    return result
