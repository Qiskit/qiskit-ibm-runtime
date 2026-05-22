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

"""Post-processing functions for converting QuantumProgramResult to primitive-specific formats."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from qiskit.primitives import PrimitiveResult

from .converters import quantum_program_item_result_to_sampler_pub_result
from .utils import executor_metadata_to_sampler_metadata, flatten_twirling_axes, undo_twirling

if TYPE_CHECKING:
    from ...results.quantum_program import QuantumProgramResult


def sampler_v2_post_processor_v0_1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert a quantum program result to a primitives result, for a V2 sampler.

    Convert :class:`~.QuantumProgramResult` to a :class:`~qiskit.primitives.PrimitiveResult`,
    for :class:`~qiskit_ibm_runtime.executor_sampler.SamplerV2`.

    This function transforms the raw quantum program execution results into the
    format expected by :class:`~qiskit_ibm_runtime.executor_sampler.SamplerV2`,
    creating :class:`~qiskit.primitives.containers.BitArray` objects and
    :class:`~qiskit.primitives.containers.SamplerPubResult` containers for each pub.

    Args:
        result: The raw quantum program result containing measurement data.

    Returns:
        Primitive result for :class:`~qiskit_ibm_runtime.executor_sampler.SamplerV2`.
    """
    if len(result) == 0:
        return PrimitiveResult([])

    if not isinstance(result.passthrough_data, dict):
        raise ValueError(
            "Wrong type for passthrough data: Expected a 'dict', found "
            f"'{type(result.passthrough_data)}'."
        )

    passthrough = cast("dict", result.passthrough_data or {})
    if (post_processor_data := passthrough.get("post_processor", None)) is None:
        raise ValueError("Missing 'post_processor' in passthrough data.")
    if (twirling := post_processor_data.get("twirling", None)) is None:
        raise ValueError("Missing 'twirling' in passthrough data.")
    if (meas_type := post_processor_data.get("meas_type", None)) is None:
        raise ValueError("Missing 'meas_type' in passthrough data.")

    # Compute the ``num_randomizations`` from the left-most axis of the result arrays
    if twirling:
        if len(set_num_randomizations := {array.shape[0] for array in result[0].values()}) != 1:
            raise ValueError("Unable to uniquely identify the number of randomizations.")
        num_randomizations = next(iter(set_num_randomizations))
    else:
        num_randomizations = 0

    # Compute the shots from the second-to-last axis of the result arrays; this corresponds to
    # PUB shots if twirling is OFF, and to ``shots_per_randomization`` if twirling is ON.
    if len(set_shots := {array.shape[-2] for array in result[0].values()}) != 1:
        raise ValueError("Unable to uniquely identify the shots per PUB.")
    shots = next(iter(set_shots))

    # Compute the shape of the input PUBs
    pub_shapes = [next(iter(item.values())).shape[1 if twirling else 0 : -2] for item in result]

    # Extract circuit metadata if present and validate length
    circuits_metadata = post_processor_data.get("circuits_metadata", None) or [None] * len(result)
    if circuits_metadata is not None and len(circuits_metadata) != len(result):
        raise ValueError(
            f"Number of circuit metadata items ({len(circuits_metadata)}) does not match "
            f"number of pubs ({len(result)})."
        )

    pub_results = []
    for item, metadatum, pub_shape in zip(result, circuits_metadata, pub_shapes):
        if len(item) == 0:
            raise ValueError("Found an item without data.")

        undo_twirling(item)

        if twirling:
            flatten_twirling_axes(item, pub_shape)

        pub_result = quantum_program_item_result_to_sampler_pub_result(item, meas_type, metadatum)
        pub_results.append(pub_result)

    metadata = executor_metadata_to_sampler_metadata(
        result.metadata, num_randomizations, shots, pub_shapes
    )

    return PrimitiveResult(pub_results, metadata=metadata or {})
