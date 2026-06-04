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

"""Conversions between different entities."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Literal

from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ...results import QuantumProgramItemResult


def expanded_values_to_lists(key_value_pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """Dict factory that converts `expanded_values` tuples to lists.

    Args:
        key_value_pairs: pairs of (key, value) items

    Returns:
        A dictionary built from `key_value_pairs`, with the key `expanded_values` containing lists.
    """
    stretch_value = dict(key_value_pairs)
    stretch_value["expanded_values"] = [list(i) for i in stretch_value["expanded_values"]]
    return stretch_value


def quantum_program_item_result_to_sampler_pub_result(
    item: QuantumProgramItemResult,
    num_randomizations: int,
    meas_type: Literal["classified", "kerneled", "avg_kerneled"] = "classified",
    circuit_metadata: dict | None = None,
) -> SamplerPubResult:
    """Convert a quantum program item result to a sampler pub result.

    Args:
        item: The result of a single item of a quantum program.
        num_randomizations: The number of randomizations.
        meas_type: The measurement type.
        circuit_metadata: The metadata attached to the circuit in the input PUB.

    Returns:
        A sampler pub result.
    """
    # Infer pub_shape from the first classical register's data
    # meas_data shape: (...pub_shape..., num_shots, num_bits)
    first_meas_data = next(iter(item.values()))
    pub_shape = first_meas_data.shape[:-2]

    arrays = {}
    for creg_name, meas_data in item.items():
        if meas_type == "classified":
            arrays[creg_name] = BitArray.from_bool_array(meas_data)
        elif meas_type == "kerneled":
            arrays[creg_name.removesuffix("_iq")] = meas_data
        elif meas_type == "avg_kerneled":
            arrays[creg_name.removesuffix("_avg_iq")] = meas_data

    data_bin = DataBin(**arrays, shape=pub_shape)

    # Construct the metadata for the result.
    pub_metadata: dict[str, Any] = {"circuit_metadata": {}}
    if circuit_metadata:
        pub_metadata["circuit_metadata"] = circuit_metadata
    if num_randomizations > 0:
        pub_metadata["num_randomizations"] = num_randomizations
    if item.metadata.scheduler_timing:
        pub_metadata.setdefault("compilation", {})
        pub_metadata["compilation"]["scheduler_timing"] = {
            "timing": item.metadata.scheduler_timing.timing,
            "circuit_duration": item.metadata.scheduler_timing.circuit_duration,
        }
    if item.metadata.stretch_values:
        pub_metadata.setdefault("compilation", {})
        pub_metadata["compilation"]["stretch_values"] = [
            asdict(stretch_value, dict_factory=expanded_values_to_lists)
            for stretch_value in item.metadata.stretch_values
        ]

    return SamplerPubResult(data=data_bin, metadata=pub_metadata)
