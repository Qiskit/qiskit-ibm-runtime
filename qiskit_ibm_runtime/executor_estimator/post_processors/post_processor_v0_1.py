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
from typing import TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from ...results.quantum_program import QuantumProgramResult

import numpy as np
from qiskit.primitives import PrimitiveResult, DataBin
from qiskit.primitives.containers.estimator_pub import ObservablesArray
from qiskit.quantum_info import Pauli

from ...utils.estimator_pub_result import EstimatorPubResult
from ..utils import (
    get_pauli_basis,
    identify_measure_basis,
    compute_exp_val,
    unbroadcast_index,
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

    if not isinstance(passthrough := result.passthrough_data, dict):
        raise ValueError(
            "Wrong type for passthrough data: Expected a 'dict', found "
            f"'{type(result.passthrough_data)}'."
        )

    if (post_processor_data := passthrough.get("post_processor", None)) is None:
        raise ValueError("Missing 'post_processor' in passthrough data.")

    # Extract data from post_processor
    if (observables_lists := post_processor_data.get("observables", None)) is None:
        raise ValueError("Missing 'observables' in post_processor data.")

    if (param_basis_pairs_lists := post_processor_data.get("param_basis_pairs", None)) is None:
        raise ValueError("Missing 'param_basis_pairs' in post_processor data.")

    if (param_shapes_list := post_processor_data.get("param_shapes", None)) is None:
        raise ValueError("Missing 'param_shapes' in post_processor data.")

    # Extract circuit metadata if present
    circuits_metadata = post_processor_data.get("circuits_metadata", None)

    # Validate circuits_metadata length if provided
    circuits_metadata = circuits_metadata or [None] * len(result)
    if {
        len(circuits_metadata),
        len(observables_lists),
        len(param_basis_pairs_lists),
        len(param_shapes_list),
    } != {len(result)}:
        raise ValueError(
            f"Number of circuit metadata items ({len(circuits_metadata)}), "
            f"observables ({len(observables_lists)}), "
            f"param_basis_pairs ({len(param_basis_pairs_lists)}), "
            f"param_shapes ({len(param_shapes_list)}), and results ({len(result)}) are not equal."
        )

    if any("_meas" not in item_result for item_result in result):
        raise ValueError("Dedicated creg `_meas` is missing from the results.")

    shots = result[0]["_meas"].shape[0] * result[0]["_meas"].shape[-2]

    # Build EstimatorPubResult for each pub
    pub_results = []
    for idx, (item_data, observables, param_basis_pairs, param_shape) in enumerate(
        zip(result, observables_lists, param_basis_pairs_lists, param_shapes_list)
    ):
        # Reconstruct observables and measure_bases
        observables = ObservablesArray(observables)
        param_shape = tuple(param_shape)

        # Get measurement data
        # Shape: (num_randomizations, num_configs, shots, num_bits)
        # where num_configs is the total number of (param_index, basis) pairs
        meas_data = item_data.pop("_meas")
        # Apply measurement flips if present
        if "measurement_flips._meas" in item_data:
            meas_data ^= item_data.pop("measurement_flips._meas")

        # Build efficient lookup: param_ndindex -> list of (measurement_basis, config_idx)
        # This allows us to find all available measurement bases for a given parameter
        config_lookup = defaultdict(list)
        for config_idx, (param_ndindex, basis_label) in enumerate(param_basis_pairs):
            config_lookup[tuple(param_ndindex)].append((Pauli(basis_label), config_idx))

        obs_shape = observables.shape
        output_shape = np.broadcast_shapes(param_shape, obs_shape)

        # Compute expectation values for all observables
        exp_vals_array = np.empty(output_shape, dtype=float)
        stds_array = np.empty(output_shape, dtype=float)

        # Loop over the broadcast output shape
        for bcast_index in np.ndindex(output_shape):
            # Unbroadcast to get the actual parameter and observable indices
            param_index = unbroadcast_index(bcast_index, param_shape)
            obs_index = unbroadcast_index(bcast_index, obs_shape)

            # Get the observable for this index
            observable = observables[obs_index]

            # Get the available (measurement_basis, config_idx) pairs for this parameter index
            try:
                param_basis_list = config_lookup[param_index]
            except KeyError:
                raise ValueError(
                    f"No measurement basis configurations found for parameter index {param_index}"
                )

            exp_val = 0.0
            variance = 0.0

            for observable_term, coeff in observable.items():
                # Find which basis can measure this term
                pauli_basis = Pauli(get_pauli_basis(observable_term))

                # Use identify_measure_basis to find the configuration index directly
                config_idx = identify_measure_basis(pauli_basis, param_basis_list)

                # Get measurement data for this configuration
                # Shape: (num_randomizations, shots, num_qubits)
                datum = meas_data[:, config_idx, :, :]
                term_exp_val, term_variance = compute_exp_val(observable_term, datum)

                # Accumulate with coefficient
                exp_val += coeff * term_exp_val
                variance += (coeff**2) * term_variance

            exp_vals_array[bcast_index] = exp_val
            stds_array[bcast_index] = np.sqrt(variance / shots)  # Standard error

        data_bin = DataBin(evs=exp_vals_array, stds=stds_array)

        # Get circuit metadata for this pub if available
        pub_metadata = {}
        if (circuit_meta := circuits_metadata[idx]) is not None:
            pub_metadata["circuit_metadata"] = circuit_meta

        pub_result = EstimatorPubResult(data=data_bin, metadata=pub_metadata)
        pub_results.append(pub_result)

    return PrimitiveResult(pub_results)
