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
from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from ...quantum_program.quantum_program_result import QuantumProgramResult

import numpy as np
from qiskit.primitives import PrimitiveResult, DataBin
from qiskit.primitives.containers.estimator_pub import ObservablesArray
from qiskit.quantum_info import PauliList, Pauli

from ...utils.estimator_pub_result import EstimatorPubResult
from ..utils import (
    get_pauli_basis,
    identify_measure_basis,
    compute_exp_val,
    broadcast_expectation_values,
)
from .registry import register_post_processor


@register_post_processor("v0.1")
def estimator_v2_post_processor_v0_1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert a quantum program result to a primitives result, for a V2 estimator.

    This function transforms the raw quantum program execution results into the
    format expected by :class:`~qiskit_ibm_runtime.executor_estimator.estimator.EstimatorV2`,
    computing expectation values from measurement data and creating
    :class:`~qiskit_ibm_runtime.utils.estimator_pub_result.EstimatorPubResult` containers
    for each pub.

    Args:
        result: The raw quantum program result containing measurement data.

    Returns:
        Primitive result.
    """
    if len(result) == 0:
        return PrimitiveResult([])

    if not isinstance(result.passthrough_data, dict):
        raise ValueError(
            "Wrong type for passthrough data: Expected a 'dict', found "
            f"'{type(result.passthrough_data)}'."
        )

    passthrough = cast(dict, result.passthrough_data)
    if (post_processor_data := passthrough.get("post_processor", None)) is None:
        raise ValueError("Missing 'post_processor' in passthrough data.")

    # Extract data from post_processor
    if (observables_lists := post_processor_data.get("observables", None)) is None:
        raise ValueError("Missing 'observables' in post_processor data.")

    if (measure_bases_lists := post_processor_data.get("measure_bases", None)) is None:
        raise ValueError("Missing 'measure_bases' in post_processor data.")

    # Extract circuit metadata if present
    circuits_metadata = post_processor_data.get("circuits_metadata", None)

    # Validate circuits_metadata length if provided
    circuits_metadata = circuits_metadata or [None] * len(result)
    if len(circuits_metadata) != len(result):
        raise ValueError(
            f"Number of circuit metadata items ({len(circuits_metadata)}) does not match "
            f"number of pubs ({len(result)})."
        )

    # Validate observables and measure_bases lengths
    if len(observables_lists) != len(result):
        raise ValueError(
            f"Number of observables lists ({len(observables_lists)}) does not match "
            f"number of pubs ({len(result)})."
        )

    if len(measure_bases_lists) != len(result):
        raise ValueError(
            f"Number of measure bases ({len(measure_bases_lists)}) does not match "
            f"number of pubs ({len(result)})."
        )

    shots = result[0]["_meas"].shape[0] * result[0]["_meas"].shape[-2]

    # Build EstimatorPubResult for each pub
    pub_results = []
    for idx, (item_data, observables, measure_bases) in enumerate(
        zip(result, observables_lists, measure_bases_lists)
    ):
        # Reconstruct observables and measure_bases
        observables = ObservablesArray(observables)
        measure_bases = PauliList(measure_bases)

        # Get measurement data
        # Shape: (num_randomizations,) + param_shape + (num_bases,) + (shots, num_bits)
        meas_data = item_data.pop("_meas")
        # Apply measurement flips if present
        if "measurement_flips._meas" in item_data:
            meas_data ^= item_data.pop("measurement_flips._meas")

        # Extract param_shape from measurement data
        param_shape = meas_data.shape[1:-3] if meas_data.ndim > 4 else ()
        obs_shape = observables.shape

        # Compute expectation values for all observables
        exp_vals_array = np.zeros(obs_shape + param_shape, dtype=float)
        stds_array = np.zeros(obs_shape + param_shape, dtype=float)

        for obs_idx, observable in np.ndenumerate(observables):
            exp_val = np.zeros(param_shape, dtype=float)
            variance = np.zeros(param_shape, dtype=float)

            for observable_term, coeff in observable.items():
                # Find which basis measured this term
                pauli_basis = Pauli(get_pauli_basis(observable_term))
                basis_idx = identify_measure_basis(pauli_basis, measure_bases)

                # Get measurement data for this basis
                # Shape: (num_randomizations) + param_shape + (shots, num_qubits)
                datum = meas_data[..., basis_idx, :, :]
                term_exp_val, term_variance = compute_exp_val(observable_term, datum)

                # Accumulate with coefficient
                exp_val = exp_val + coeff * term_exp_val
                variance = variance + (coeff**2) * term_variance

            exp_vals_array[obs_idx] = exp_val
            stds_array[obs_idx] = np.sqrt(variance / shots)  # Standard error

        # Broadcast expectation values and standard deviations to output shape
        exp_vals_array, stds_array = broadcast_expectation_values(
            exp_vals_array, stds_array, param_shape, obs_shape
        )

        data_bin = DataBin(
            evs=exp_vals_array,
            stds=stds_array,
        )

        # Get circuit metadata for this pub if available
        pub_metadata = {}
        if (circuit_meta := circuits_metadata[idx]) is not None:
            pub_metadata["circuit_metadata"] = circuit_meta

        pub_result = EstimatorPubResult(data=data_bin, metadata=pub_metadata)
        pub_results.append(pub_result)

    return PrimitiveResult(pub_results, metadata=result.metadata or {})
