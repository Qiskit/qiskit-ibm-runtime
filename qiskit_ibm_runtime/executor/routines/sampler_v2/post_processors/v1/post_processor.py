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
from ....options.sampler_options import SamplerOptions
from ..utils import register_post_processor
from .executor_metadata_to_sampler_metadata import executor_metadata_to_sampler_metadata
from .flatten_twirling_axes import flatten_twirling_axes


@register_post_processor("v1")
def sampler_v2_post_processor_v1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert QuantumProgramResult to SamplerV2 PrimitiveResult.

    This function transforms the raw quantum program execution results into the
    format expected by SamplerV2, creating BitArray objects and SamplerPubResult
    containers for each pub.

    When twirling is enabled, the executor returns measurement data with a leading
    ``num_randomizations`` axis. This function flattens that axis together with the
    ``shots_per_randomization`` axis into a single ``total_shots`` axis.

    Flattening is performed when twirling is enabled (determined by checking the
    ``options`` field in ``result.passthrough_data["post_processor"]``). The
    ``pub_shapes`` field provides the parameter sweep shape for each pub.

    Args:
        result: The raw quantum program result containing measurement data.

    Returns:
        PrimitiveResult containing SamplerPubResult objects.
    """

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
    if (options_dict := post_processor_data.get("options", None)) is None:
        raise ValueError("Missing 'options' in passthrough data.")
    if (pub_shapes := post_processor_data.get("pub_shapes", None)) is None:
        raise ValueError("Missing 'pub_shapes' in passthrough data.")
    if len(pub_shapes) != len(result):
        raise ValueError(f"Expected 'pub_shape' of length {len(result)}, found {len(pub_shapes)}.")
    pub_shapes = [tuple(pub_shape) for pub_shape in pub_shapes]

    try:
        options = SamplerOptions(**options_dict)
    except (TypeError, ValueError) as ex:
        raise ValueError("Couldn't initialize SamplerOptions from 'options_dict'.") from ex

    # Compute the shots from the second-to-last axis of the result arrays; this corresponds to
    # PUB shots if twirling is OFF, and to ``shots_per_randomization`` if twirling is ON.
    if len(set_shots := {array.shape[-2] for array in result[0].values()}) != 1:
        raise ValueError("Unable to uniquely identify the shots per PUB.")
    shots = next(iter(set_shots))

    # Compute the ``num_randomizations`` from the left-most axis of the result arrays
    if options.twirling.enable_gates or options.twirling.enable_measure:
        if len(set_num_randomizations := {array.shape[0] for array in result[0].values()}) != 1:
            raise ValueError("Unable to uniquely identity the number of randomizations.")
        num_randomizations = next(iter(set_num_randomizations))
    else:
        num_randomizations = 0

    if options.twirling.enable_gates or options.twirling.enable_measure:
        for item, shape in zip(result, pub_shapes):
            flatten_twirling_axes(item, shape)

    metadata = executor_metadata_to_sampler_metadata(
        result.metadata, num_randomizations, shots, pub_shapes
    )

    sampler_result = SamplerV2.quantum_program_result_to_primitive_result(result, metadata)
    return sampler_result
