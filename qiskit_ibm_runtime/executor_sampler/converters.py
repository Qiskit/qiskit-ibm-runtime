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

from qiskit.primitives import PrimitiveResult
from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult

from ..options_models import EnvironmentOptions, ExecutionOptions, ExecutorOptions

if TYPE_CHECKING:
    from ..options_models import SamplerOptions
    from ..quantum_program import QuantumProgramResult


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


def quantum_program_result_to_primitive_result(
    result: QuantumProgramResult,
    metadata: dict[str, Any] | None = None,
    meas_type: Literal["classified", "kerneled", "avg_kerneled"] = "classified",
    circuits_metadata: list[dict] | None = None,
) -> PrimitiveResult:
    """Convert :class:`~.QuantumProgramResult` to :class:`~qiskit.primitives.PrimitiveResult`.

    Args:
        result: The (possibly post-processed) quantum program result.
        metadata: The metadata to attach to the result.
        meas_type: How to process and return measurement results. This option sets the return
            type of all classical registers in all sampler pub results.

        * ``"classified"``: Returns a BitArray with classified measurement outcomes.
        * ``"kerneled"``: Returns complex IQ data points from kerneling the measurement
            trace, in arbitrary units.
        * ``"avg_kerneled"``: Returns complex IQ data points averaged over shots,
            in arbitrary units.
        circuits_metadata: Optional list of circuit metadata dicts, one per pub.

    Returns:
        The converted primitive result.

    Raises:
        ValueError: If data is malformed or inconsistent, or if ``circuits_metadata``
            length doesn't match number of pubs.
    """
    # Validate circuits_metadata length if provided
    circuits_metadata = circuits_metadata or [None] * len(result)
    if circuits_metadata is not None and len(circuits_metadata) != len(result):
        raise ValueError(
            f"Number of circuit metadata items ({len(circuits_metadata)}) does not match "
            f"number of pubs ({len(result)})."
        )

    # Build SamplerPubResult for each pub
    pub_results = []
    for idx, item_data in enumerate(result):
        # Validate that measurement data exists
        if not item_data:
            raise ValueError(f"Pub {idx} has no measurement data")

        # Infer pub_shape from the first classical register's data
        # meas_data shape: (...pub_shape..., num_shots, num_bits)
        first_meas_data = next(iter(item_data.values()))
        pub_shape = first_meas_data.shape[:-2]

        arrays = {}
        for creg_name, meas_data in item_data.items():
            if meas_type == "classified":
                arrays[creg_name] = BitArray.from_bool_array(meas_data)
            elif meas_type == "kerneled":
                arrays[creg_name.removesuffix("_iq")] = meas_data
            elif meas_type == "avg_kerneled":
                arrays[creg_name.removesuffix("_avg_iq")] = meas_data

        data_bin = DataBin(**arrays, shape=pub_shape)

        # Get circuit metadata for this pub if available
        pub_metadata = {}
        if circuits_metadata is not None:
            circuit_meta = circuits_metadata[idx]
            if circuit_meta is not None:
                pub_metadata["circuit_metadata"] = circuit_meta

        pub_result = SamplerPubResult(data=data_bin, metadata=pub_metadata)
        pub_results.append(pub_result)

    return PrimitiveResult(pub_results, metadata=metadata or {})
