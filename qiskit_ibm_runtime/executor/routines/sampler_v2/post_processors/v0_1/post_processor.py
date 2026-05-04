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
from typing import cast

from qiskit.primitives import PrimitiveResult

from ......quantum_program.quantum_program_result import QuantumProgramResult
from ...sampler import SamplerV2
from ..utils import register_post_processor
from .executor_metadata_to_sampler_metadata import executor_metadata_to_sampler_metadata
from .flatten_twirling_axes import flatten_twirling_axes


@register_post_processor("v0.1")
def sampler_v2_post_processor_v0_1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert a quantum program result to a primitives result, for a V2 sampler.

    Convert :class:`~.QuantumProgramResult` to a :class:`~qiskit.primitives.PrimitiveResult`,
    for :class:`~qiskit_ibm_runtime.executor.routines.sampler_v2.SamplerV2`.

    This function transforms the raw quantum program execution results into the
    format expected by :class:`~qiskit_ibm_runtime.executor.routines.sampler_v2.SamplerV2`,
    creating :class:`~qiskit.primitives.containers.BitArray` objects and
    :class:`~qiskit.primitives.containers.SamplerPubResult` containers for each pub.

    Args:
        result: The raw quantum program result containing measurement data.

    Returns:
        Primitive result for :class:`~qiskit_ibm_runtime.executor.routines.sampler_v2.SamplerV2`.
    """
    if len(result) == 0:
        return PrimitiveResult([])

    # Apply measurement twirling bit flips
    prefix = "measurement_flips."
    for item in result:
        for key in list(item.keys()):
            if key.startswith(prefix):
                item[key[len(prefix) :]] ^= item.pop(key)
    # TODO: This could fail if the user manually specifies a register starting with the prefix.

    if not isinstance(result.passthrough_data, dict):
        raise ValueError(
            "Wrong type for passthrough data: Expected a 'dict', found "
            f"'{type(result.passthrough_data)}'."
        )

    passthrough = cast(dict, result.passthrough_data or {})
    if (post_processor_data := passthrough.get("post_processor", None)) is None:
        raise ValueError("Missing 'post_processor' in passthrough data.")
    if (twirling := post_processor_data.get("twirling", None)) is None:
        raise ValueError("Missing 'twirling' in passthrough data.")
    if (meas_type := post_processor_data.get("meas_type", None)) is None:
        raise ValueError("Missing 'meas_type' in passthrough data.")

    # Extract circuit metadata if present
    circuits_metadata = post_processor_data.get("circuits_metadata", None)

    # Remove suffixes from register names for kerneled measurements
    if meas_type in ("kerneled", "avg_kerneled"):
        suffix = "_avg_iq" if meas_type == "avg_kerneled" else "_iq"
        for item in result:
            for key in list(item.keys()):
                if key.endswith(suffix):
                    new_key = key[: -len(suffix)]
                    item[new_key] = item.pop(key)

    # TODO: This will fail for PUBs with no measurements, but it will also fail in many other
    # places.
    pub_shapes = [next(iter(item.values())).shape[1 if twirling else 0 : -2] for item in result]

    # Compute the shots from the second-to-last axis of the result arrays; this corresponds to
    # PUB shots if twirling is OFF, and to ``shots_per_randomization`` if twirling is ON.
    if len(set_shots := {array.shape[-2] for array in result[0].values()}) != 1:
        raise ValueError("Unable to uniquely identify the shots per PUB.")
    shots = next(iter(set_shots))

    # Compute the ``num_randomizations`` from the left-most axis of the result arrays
    if twirling:
        if len(set_num_randomizations := {array.shape[0] for array in result[0].values()}) != 1:
            raise ValueError("Unable to uniquely identity the number of randomizations.")
        num_randomizations = next(iter(set_num_randomizations))
    else:
        num_randomizations = 0

    if twirling:
        for item, shape in zip(result, pub_shapes):
            flatten_twirling_axes(item, shape)

    metadata = executor_metadata_to_sampler_metadata(
        result.metadata, num_randomizations, shots, pub_shapes
    )

    sampler_result = SamplerV2.quantum_program_result_to_primitive_result(
        result, metadata, meas_type, circuits_metadata
    )
    return sampler_result
