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

from typing import TYPE_CHECKING, Literal

from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult

if TYPE_CHECKING:
    from ...results import QuantumProgramItemResult


def quantum_program_item_result_to_sampler_pub_result(
    item: QuantumProgramItemResult,
    meas_type: Literal["classified", "kerneled", "avg_kerneled"] = "classified",
    circuit_metadata: dict | None = None,
) -> SamplerPubResult:
    """Convert a quantum program item result to a sampler pub result.

    Args:
        item: The result of a single item of a quantum program.
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

    # Get circuit metadata for this pub if available
    pub_metadata = {}
    if circuit_metadata is not None:
        pub_metadata["circuit_metadata"] = circuit_metadata

    return SamplerPubResult(data=data_bin, metadata=pub_metadata)
