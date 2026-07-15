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

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy.typing as npt
    from qiskit.quantum_info import PauliLindbladMap

    from ...options_models.zne_options import ExtrapolatorType
    from ...results.quantum_program import QuantumProgramItemResult

import numpy as np
from qiskit.primitives import DataBin, PrimitiveResult
from qiskit.primitives.containers.estimator_pub import ObservablesArray
from qiskit.quantum_info import Pauli

from ...executor_estimator.utils import get_pauli_basis, unbroadcast_index
from ...executor_estimator.zne.extrapolation import process_extrapolated_expectation_values
from ...results.estimator_pub import EstimatorPubResult
from ...results.quantum_program import QuantumProgramResult
from .trex_utils import calculate_trex_factor, get_processed_calibration_data
from .utils import compute_exp_val, identify_measure_basis


def estimator_v2_post_processor_v0_1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert a quantum program result to a primitives result, for a V2 estimator.

    This function transforms the raw quantum program execution results into the
    format expected by :class:`~qiskit_ibm_runtime.executor_estimator.estimator.EstimatorV2`,
    computing expectation values from measurement data and creating
    :class:`~qiskit_ibm_runtime.results.EstimatorPubResult` containers
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

    # Extract options if present
    options_metadata = post_processor_data.get("options", {})

    # Extract mitigation data
    mitigation = post_processor_data.get("mitigation", None)
    pec_gammas = post_processor_data.get("pec_gammas", None)

    # Check if measure_mitigation was used
    measure_mitigation = post_processor_data.get("measure_mitigation", None)
    readout_noise_data = None
    if measure_mitigation == "True":
        # assume a calibration circuit was added to the quantum program as the last item
        calibration_result = result[-1]
        try:
            readout_noise_data = get_processed_calibration_data(calibration_result)
        except ValueError as e:
            raise ValueError(f"Failed calculating TREX noise model. Internal failure: {e}")

        # create a result object without the calibration item
        result = QuantumProgramResult(
            data=list(result[:-1]),
            metadata=result.metadata,
            passthrough_data=result.passthrough_data,
        )

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

    # Build EstimatorPubResult for each pub
    pub_results = []
    for idx, (item_result, observables_label, param_basis_pairs, param_shape) in enumerate(
        zip(result, observables_lists, param_basis_pairs_lists, param_shapes_list)
    ):
        # Reconstruct observables and measure_bases
        observables = ObservablesArray(observables_label)
        param_shape = tuple(param_shape)

        # Calculate exp vals and build an EstimatorPubResult
        if mitigation == "pec":
            pub_result = create_pub_result_pec(
                item_result,
                observables,
                param_shape,
                param_basis_pairs,
                readout_noise_data,
                pec_gamma=pec_gammas[idx],
            )
        elif mitigation is not None:
            raise ValueError(f"Unknown mitigation technique {mitigation}")
        else:
            pub_result = create_pub_result(
                item_result, observables, param_shape, param_basis_pairs, readout_noise_data
            )

        # Attach circuit metadata (shared across all branches — metadata is mutable)
        if (circuit_meta := circuits_metadata[idx]) is not None:
            pub_result.metadata["circuit_metadata"] = circuit_meta
        pub_results.append(pub_result)

    return PrimitiveResult(pub_results, metadata=options_metadata)


def _process_expectation_values(
    item_result: QuantumProgramItemResult,
    observables: ObservablesArray,
    param_shape: tuple[int, ...],
    param_basis_pairs: list[tuple[tuple[int, ...], str]],
    measure_noise_data: PauliLindbladMap | np.ndarray | None,
) -> tuple[npt.NDArray[float], npt.NDArray[float], npt.NDArray[float]]:
    """Process expectation values for a single item result.

    Args:
        item_result: The item result.
        observables: The observables to calculate expectation values for.
        param_shape: The shape of the parameter values in the original PUB.
        param_basis_pairs: The map between params ndindexes to basis.
        measure_noise_data: Measurement noise calibration data for TREX mitigation. Can be either a
            PauliLindbladMap of a noise model learned upfront, or a result of a calibration circuit.

    Returns:
        A tuple ``(exp_vals, stds, ensemble_stds)``, where ``exp_vals`` are expectation values,
        ``stds`` are standard deviations, and ``ensemble_stds`` are ensemble standard errors.

    Raises:
        ValueError: If ``item_result`` has no ``'_meas'`` key.
        ValueError: If ``item_result['_meas']`` has a number of axis not equal to ``4``.
        ValueError: If ``param_shape`` and ``observables.shape`` cannot be broadcasted against
            each other.
    """
    try:
        data = item_result["_meas"]
    except KeyError:
        raise ValueError("Dedicated creg ``'_meas'`` is missing from the results.")

    if data.ndim != 4:
        # Shape: (num_randomizations, num_configs, shots, num_bits)
        # where num_configs is the total number of (param_index, basis) pairs
        raise ValueError(f"``item_result['_meas']`` has ``{data.ndim}`` axes, expected ``4``.")

    # Get number of randomizations and shots per randomization
    num_randomizations = data.shape[0]
    shots_per_randomization = data.shape[-2]
    total_shots = num_randomizations * shots_per_randomization

    # Apply measurement flips if present
    if "measurement_flips._meas" in item_result:
        data ^= item_result["measurement_flips._meas"]

    # Build efficient lookup: param_ndindex -> list of (measurement_basis, config_idx)
    # This allows us to find all available measurement bases for a given parameter
    config_lookup = defaultdict(list)
    for config_idx, (param_ndindex, basis_label) in enumerate(param_basis_pairs):
        config_lookup[tuple(param_ndindex)].append((Pauli(basis_label), config_idx))

    try:
        output_shape = np.broadcast_shapes(param_shape, observables.shape)
    except ValueError:
        raise ValueError(
            f"Cannot broadcast ``param_shape`` {param_shape} and ``observables`` shape "
            f"{observables.shape}"
        )

    # Compute expectation values for all observables
    exp_vals = np.empty(output_shape, dtype=float)
    stds = np.empty(output_shape, dtype=float)
    ensemble_stds = np.empty(output_shape, dtype=float)

    # Loop over the broadcast output shape
    for bcast_index in np.ndindex(output_shape):
        # Unbroadcast to get the actual parameter and observable indices
        param_index = unbroadcast_index(bcast_index, param_shape)
        obs_index = unbroadcast_index(bcast_index, observables.shape)

        # Get the observable for this index
        observable = observables[obs_index]

        # Get the available (measurement_basis, config_idx) pairs for this parameter index
        try:
            param_basis_list = config_lookup[param_index]  # type: ignore[index]
        except KeyError:
            raise ValueError(
                f"No measurement basis configurations found for parameter index {param_index}"
            )

        exp_val = 0.0
        ensemble_variance = 0.0
        twirl_variance = 0.0
        for observable_term, coeff in observable.items():
            # Find which basis can measure this term
            pauli_basis = Pauli(get_pauli_basis(observable_term))

            # Use identify_measure_basis to find the configuration index directly
            config_idx = identify_measure_basis(pauli_basis, param_basis_list)

            # Get measurement data for this configuration
            # datum shape: (num_randomizations, shots_per_randomization, num_qubits)
            datum = data[:, config_idx, :, :]
            term_exp_val, term_ensemble_variance, term_twirl_variance = compute_exp_val(
                observable_term, datum
            )

            # Calculate scale factor in case TREX mitigation is used
            term_scale_factor = (
                calculate_trex_factor(measure_noise_data, observable_term)
                if measure_noise_data is not None
                else 1
            )

            # Accumulate with coefficient
            exp_val += coeff * term_exp_val * term_scale_factor
            ensemble_variance += (coeff**2) * term_ensemble_variance * (term_scale_factor**2)
            twirl_variance += (coeff**2) * term_twirl_variance * (term_scale_factor**2)

        exp_vals[bcast_index] = exp_val
        ensemble_stds[bcast_index] = np.sqrt(ensemble_variance / total_shots)
        # When twirling is off (num_randomizations=1), stds equals ensemble_standard_error
        if num_randomizations == 1:
            stds[bcast_index] = ensemble_stds[bcast_index]
        else:
            stds[bcast_index] = np.sqrt(twirl_variance / num_randomizations)

    return exp_vals, stds, ensemble_stds


def _process_expectation_values_pec(
    item_result: QuantumProgramItemResult,
    observables: ObservablesArray,
    param_shape: tuple[int, ...],
    param_basis_pairs: list[tuple[tuple[int, ...], str]],
    measure_noise_data: PauliLindbladMap | np.ndarray | None,
    pec_gamma: float,
) -> tuple[npt.NDArray[float], npt.NDArray[float], npt.NDArray[float]]:
    """Process expectation values for a single item pec mitigated result.

    Args:
        item_result: The item result.
        observables: The observables to calculate expectation values for.
        param_shape: The shape of the parameter values in the original PUB.
        param_basis_pairs: The map between params ndindexes to basis.
        measure_noise_data: Measurement noise calibration data for TREX mitigation. Can be either a
            PauliLindbladMap of a noise model learned upfront, or a result of a calibration circuit.
        pec_gamma: gamma factor for PEC mitigation.

    Returns:
        A tuple ``(exp_vals, stds, ensemble_stds)``, where ``exp_vals`` are expectation values,
        ``stds`` are standard deviations, and ``ensemble_stds`` are ensemble standard errors.

    Raises:
        ValueError: If ``item_result`` has no ``'_meas'`` key.
        ValueError: If ``item_result['_meas']`` has a number of axis not equal to ``4``.
        ValueError: If ``item_result`` has no ``'pauli_signs'`` key.
        ValueError: If ``param_shape`` and ``observables.shape`` cannot be broadcasted against
            each other.
    """
    try:
        data = item_result["_meas"]
    except KeyError:
        raise ValueError("Dedicated creg ``'_meas'`` is missing from the results.")

    if data.ndim != 4:
        # Shape: (num_randomizations, num_configs, shots, num_bits)
        # where num_configs is the total number of (param_index, basis) pairs
        raise ValueError(f"``item_result['_meas']`` has ``{data.ndim}`` axes, expected ``4``.")

    # Get number of randomizations and shots per randomization
    num_randomizations = data.shape[0]
    shots_per_randomization = data.shape[-2]
    total_shots = num_randomizations * shots_per_randomization

    # Apply measurement flips if present
    if "measurement_flips._meas" in item_result:
        data ^= item_result["measurement_flips._meas"]

    # extract pec signs if present
    pec_signs = item_result.get("pauli_signs", None)
    if pec_signs is None:
        raise ValueError("Results must contain ``'pauli_signs'`` in the data if PEC is used.")

    # Build efficient lookup: param_ndindex -> list of (measurement_basis, config_idx)
    # This allows us to find all available measurement bases for a given parameter
    config_lookup = defaultdict(list)
    for config_idx, (param_ndindex, basis_label) in enumerate(param_basis_pairs):
        config_lookup[tuple(param_ndindex)].append((Pauli(basis_label), config_idx))

    try:
        output_shape = np.broadcast_shapes(param_shape, observables.shape)
    except ValueError:
        raise ValueError(
            f"Cannot broadcast ``param_shape`` {param_shape} and ``observables`` shape "
            f"{observables.shape}"
        )

    # Compute expectation values for all observables
    exp_vals = np.empty(output_shape, dtype=float)
    stds = np.empty(output_shape, dtype=float)
    ensemble_stds = np.empty(output_shape, dtype=float)

    # Loop over the broadcast output shape
    for bcast_index in np.ndindex(output_shape):
        # Unbroadcast to get the actual parameter and observable indices
        param_index = unbroadcast_index(bcast_index, param_shape)
        obs_index = unbroadcast_index(bcast_index, observables.shape)

        # Get the observable for this index
        observable = observables[obs_index]

        # Get the available (measurement_basis, config_idx) pairs for this parameter index
        try:
            param_basis_list = config_lookup[param_index]  # type: ignore[index]
        except KeyError:
            raise ValueError(
                f"No measurement basis configurations found for parameter index {param_index}"
            )

        exp_val = 0.0
        ensemble_variance = 0.0
        twirl_variance = 0.0
        for observable_term, coeff in observable.items():
            # Find which basis can measure this term
            pauli_basis = Pauli(get_pauli_basis(observable_term))

            # Use identify_measure_basis to find the configuration index directly
            config_idx = identify_measure_basis(pauli_basis, param_basis_list)

            # get the signs for this configuration
            pec_signs_datum = pec_signs[:, config_idx, :]

            # Get measurement data for this configuration
            # Shape: (num_randomizations, shots, num_qubits)
            datum = data[:, config_idx, :, :]
            term_exp_val, term_ensemble_variance, term_twirl_variance = compute_exp_val(
                observable_term, datum, pec_signs_datum
            )

            # Calculate scale factor in case TREX mitigation is used
            term_scale_factor = (
                calculate_trex_factor(measure_noise_data, observable_term)
                if measure_noise_data is not None
                else 1
            )

            # Accumulate with coefficient
            exp_val += coeff * term_exp_val * term_scale_factor
            ensemble_variance += (coeff**2) * term_ensemble_variance * term_scale_factor**2
            twirl_variance += (coeff**2) * term_twirl_variance * term_scale_factor**2

        exp_vals[bcast_index] = exp_val * pec_gamma
        ensemble_stds[bcast_index] = np.sqrt(ensemble_variance * pec_gamma**2 / total_shots)
        stds[bcast_index] = np.sqrt(twirl_variance * pec_gamma**2 / num_randomizations)

    return exp_vals, stds, ensemble_stds


def create_pub_result(
    item_result: QuantumProgramItemResult,
    observables: ObservablesArray,
    param_shape: tuple[int, ...],
    param_basis_pairs: list[tuple[tuple[int, ...], str]],
    measure_noise_data: PauliLindbladMap | np.ndarray | None,
) -> EstimatorPubResult:
    """Calculate expectation values and errors, and return pub result.

    Args:
        item_result: The item result.
        observables: The observables to calculate expectation values for.
        param_shape: The shape of the parameter values in the original PUB.
        param_basis_pairs: The map between params ndindexes to basis.
        measure_noise_data: Measurement noise calibration data for TREX mitigation.

    Returns:
        An :class:`~qiskit_ibm_runtime.results.EstimatorPubResult` with an empty metadata dict.
    """
    exp_vals, stds, ensemble_stds = _process_expectation_values(
        item_result, observables, param_shape, param_basis_pairs, measure_noise_data
    )
    data_bin = DataBin(
        evs=exp_vals, stds=stds, ensemble_standard_error=ensemble_stds, shape=exp_vals.shape
    )
    return EstimatorPubResult(data=data_bin)


def create_pub_result_pec(
    item_result: QuantumProgramItemResult,
    observables: ObservablesArray,
    param_shape: tuple[int, ...],
    param_basis_pairs: list[tuple[tuple[int, ...], str]],
    measure_noise_data: PauliLindbladMap | np.ndarray | None,
    pec_gamma: float,
) -> EstimatorPubResult:
    """Calculate expectation values and errors with PEC, and return pub result.

    Args:
        item_result: The item result.
        observables: The observables to calculate expectation values for.
        param_shape: The shape of the parameter values in the original PUB.
        param_basis_pairs: The map between params ndindexes to basis.
        measure_noise_data: Measurement noise calibration data for TREX mitigation.
        pec_gamma: Gamma factor for PEC mitigation.

    Returns:
        An :class:`~qiskit_ibm_runtime.results.EstimatorPubResult` with an empty metadata dict.
    """
    exp_vals, stds, ensemble_stds = _process_expectation_values_pec(
        item_result, observables, param_shape, param_basis_pairs, measure_noise_data, pec_gamma
    )
    data_bin = DataBin(
        evs=exp_vals, stds=stds, ensemble_standard_error=ensemble_stds, shape=exp_vals.shape
    )
    return EstimatorPubResult(data=data_bin)


def calculate_extrapolated_expectation_values(
    noise_amplified_data: np.ndarray,
    observables: ObservablesArray,
    param_shape: tuple[int, ...],
    param_basis_pairs: list[tuple[tuple[int, ...], str]],
    noise_factors: list[float],
    extrapolated_noise_factors: list[float],
    extrapolator: list[ExtrapolatorType],
    measure_noise_data: PauliLindbladMap | np.ndarray | None,
) -> tuple[npt.NDArray[float], npt.NDArray[float], npt.NDArray[float], list[list[str]]]:
    """Calculate expectation values for given data, observables and params.

    Args:
        noise_amplified_data: The measured data result. Its shape should be:
            ``(noise_factors, num_randomizations, num_configs, shots, num_bits)``
        observables: The observables to calculate expectation values for.
        param_shape: The shape of the parameter values in the original PUB.
        param_basis_pairs: The map between params ndindexes to basis.
        noise_factors: The noise factors used to amplify the noise.
        extrapolated_noise_factors: Noise factors to evaluate the fits at.
        extrapolator: The extrapolator model or models to use. Models will be tried in priority
            order. Supported models (each fits the named function of the noise factor ``x``):
            - ```"linear"``: ``a + b*x``
            - ``"polynomial_degree_k"`` (1 <= k <= 7): a degree-k polynomial
            - ``"exponential"``: ``a*exp(b*x)``
            - ``"double_exponential"``: ``a*exp(b*x) + c*exp(d*x)`` (rates constrained to decay)
            - ``"fallback"``: no fit; the measured value at the lowest noise factor
        measure_noise_data: Measurement noise calibration data for TREX mitigation. Can be either a
            PauliLindbladMap of a noise model learned upfront, or a result of a calibration circuit.

    Returns:
        A tuple ``(exp_vals, stds, ensemble_stds)``, where ``exp_vals`` are expectation values,
        ``stds`` are standard deviations, and ``ensemble_stds`` are ensemble standard errors.

    Raises:
        ValueError: If ``param_shape`` and ``observables.shape`` cannot be broadcasted against
            each other.
    """
    # Get number of randomizations and shots per randomization
    num_randomizations = noise_amplified_data.shape[1]

    # Build efficient lookup: param_ndindex -> list of (measurement_basis, config_idx)
    # This allows us to find all available measurement bases for a given parameter
    config_lookup = defaultdict(list)
    for config_idx, (param_ndindex, basis_label) in enumerate(param_basis_pairs):
        config_lookup[tuple(param_ndindex)].append((Pauli(basis_label), config_idx))

    try:
        output_shape = np.broadcast_shapes(param_shape, observables.shape)
    except ValueError:
        raise ValueError(
            f"Cannot broadcast ``param_shape`` {param_shape} and ``observables`` shape "
            f"{observables.shape}"
        )

    # Compute expectation values for all observables
    exp_vals = np.empty(shape=(len(extrapolated_noise_factors),) + output_shape, dtype=float)
    stds = np.empty(shape=(len(extrapolated_noise_factors),) + output_shape, dtype=float)
    ensemble_stds = np.empty(shape=(len(extrapolated_noise_factors),) + output_shape, dtype=float)
    selected_extrapolators = []

    # Loop over the broadcast output shape
    for bcast_index in np.ndindex(output_shape):
        # Unbroadcast to get the actual parameter and observable indices
        param_index = unbroadcast_index(bcast_index, param_shape)
        obs_index = unbroadcast_index(bcast_index, observables.shape)

        # Get the observable for this index
        observable = observables[obs_index]

        # Get the available (measurement_basis, config_idx) pairs for this parameter index
        try:
            param_basis_list = config_lookup[param_index]  # type: ignore[index]
        except KeyError:
            raise ValueError(
                f"No measurement basis configurations found for parameter index {param_index}"
            )

        # each item should contain results for each point in extrapolated_noise_factors
        exp_vals_extrapolated = np.zeros(len(extrapolated_noise_factors), dtype=float)
        ensemble_std_extrapolated = np.zeros(len(extrapolated_noise_factors), dtype=float)
        twirl_variance_extrapolated = np.zeros(len(extrapolated_noise_factors), dtype=float)
        selected_extrapolators_per_term = []

        for observable_term, coeff in observable.items():
            # Find which basis can measure this term
            pauli_basis = Pauli(get_pauli_basis(observable_term))

            # Use identify_measure_basis to find the configuration index directly
            config_idx = identify_measure_basis(pauli_basis, param_basis_list)

            noise_scaled_exp_vals = []
            noise_scaled_ensemble_std = []
            non_amplified_twirl_var = 0.0
            for noise_factor_index in range(len(noise_factors)):
                noise_factor_data = noise_amplified_data[noise_factor_index]
                # Get measurement data for this configuration
                # datum shape: (num_randomizations, shots_per_randomization, num_qubits)
                datum = noise_factor_data[:, config_idx, :, :]
                term_exp_val, term_ensemble_variance, term_twirl_variance = compute_exp_val(
                    observable_term, datum
                )
                noise_scaled_exp_vals.append(term_exp_val)
                noise_scaled_ensemble_std.append(np.sqrt(term_ensemble_variance))
                if noise_factors[noise_factor_index] == 1:
                    non_amplified_twirl_var = term_twirl_variance

            extrap_exp_vals, extrap_stds, sel_extrapolators = (
                process_extrapolated_expectation_values(
                    noise_scaled_exp_vals,
                    noise_scaled_ensemble_std,
                    observable_term,
                    noise_factors,
                    extrapolator,
                    extrapolated_noise_factors,
                )
            )

            selected_extrapolators_per_term.append(sel_extrapolators)

            # Calculate scale factor in case TREX mitigation is used
            term_scale_factor = (
                calculate_trex_factor(measure_noise_data, observable_term)
                if measure_noise_data is not None
                else 1
            )
            for extrap_index, (extrap_exp_val, extrap_std) in enumerate(
                zip(extrap_exp_vals, extrap_stds)
            ):
                # Accumulate with coefficient
                exp_vals_extrapolated[extrap_index] += coeff * extrap_exp_val * term_scale_factor
                # failed extrapolation might return NaN as std
                if not np.isnan(extrap_std):
                    ensemble_std_extrapolated[extrap_index] += (
                        coeff * extrap_std * term_scale_factor
                    )
                twirl_variance_extrapolated[extrap_index] += (
                    (coeff**2) * non_amplified_twirl_var * (term_scale_factor**2)
                )

        exp_vals[(slice(None), *bcast_index)] = exp_vals_extrapolated
        ensemble_stds[(slice(None), *bcast_index)] = ensemble_std_extrapolated
        # When twirling is off (num_randomizations=1), stds equals ensemble_standard_error
        if num_randomizations == 1:
            stds[(slice(None), *bcast_index)] = ensemble_stds[(slice(None), *bcast_index)]
        else:
            stds[(slice(None), *bcast_index)] = np.sqrt(
                twirl_variance_extrapolated / num_randomizations
            )
        selected_extrapolators.append(selected_extrapolators_per_term)

    return exp_vals, stds, ensemble_stds, selected_extrapolators
