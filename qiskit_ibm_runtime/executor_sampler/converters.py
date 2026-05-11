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
from typing import TYPE_CHECKING, Literal

from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult

from ..options_models import EnvironmentOptions, ExecutionOptions, ExecutorOptions

if TYPE_CHECKING:
    from ..options_models import SamplerOptions
    from ..quantum_program import QuantumProgramItemResult


def sampler_options_to_executor_options(options: SamplerOptions) -> ExecutorOptions:
    """Map sampler options to executor options, ignoring all irrelevant fields.

    Args:
        options: Instance of sampler options.

    Returns:
        Mapped executor options.
    """
    executor_options = ExecutorOptions()

    environment_options = asdict(options.environment)  # type: ignore[call-overload]
    execution_options = asdict(options.execution)  # type: ignore[call-overload]
    execution_options.pop("meas_type")
    executor_options.environment = EnvironmentOptions(**environment_options)
    executor_options.execution = ExecutionOptions(**execution_options)

    executor_options.environment.max_execution_time = options.max_execution_time
    if options.experimental:
        executor_options.environment.image = options.experimental.pop("image", None)
        executor_options.experimental.update(options.experimental)

    return executor_options


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
