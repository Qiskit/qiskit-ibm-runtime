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

"""Helper functions for the PEC error mitigation method."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from qiskit.quantum_info import PauliLindbladMap

    from ...options_models.measure_noise_learning_options import MeasureNoiseLearningOptions
    from ...options_models.pec_options import PecOptions
    from ...options_models.twirling_options import TwirlingOptions

import numpy as np
from samplomatic import build

from ...exceptions import IBMInputValueError
from ...quantum_program import QuantumProgram
from ...quantum_program.quantum_program import SamplexItem
from ..trex_utils import create_trex_calibration_circuit, resolve_trex_num_randomizations
from ..utils import (
    box_circuit,
    compute_samplex_arguments,
    make_samplex_arguments,
    options_to_boxing_pm_kwargs,
)
from .utils import calculate_gamma, calculate_pec_twirling_shots

logger = logging.getLogger(__name__)


def prepare_pec(
    pubs: Sequence[EstimatorPub],
    twirling_options: TwirlingOptions,
    shots: int,
    pec_options: PecOptions,
    noise_model_mapping: dict[str, PauliLindbladMap],
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
    add_tags: bool = False,
) -> QuantumProgram:
    """Convert estimator PUBs to a quantum program with PEC mitigation.

    Args:
        pubs: List of estimator pubs to convert.
        twirling_options: The twirling options.
        shots: The number of pre-overhead shots to use. Will be overridden by
            ``num_randomizations * shots_per_randomization`` when both are specified explicitly.
            The number of shots of each pub will be multiplied by the sampling overhead of gamma^2.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be used.
        pec_options: The options for PEC mitigation.
        noise_model_mapping: Mapping between layer ref to a noise model to use for PEC mitigation
            method. The dict contains layers from all pubs. Assumes that the unique layers
            used for noise learning were extracted using the ``find_unique_layers`` method.
        add_tags: Whether to include tags for the boxes. Relevant mainly for debugging.
            ``False`` will cause no tags to be added (will pass the "none" value to the relevant
            attribute), while ``True`` will cause tags with the twirled boxes hash to be added
            (using the "unique_box" value of the relevant attribute). These tags can help
            injecting noise in simulators.

    Returns:
        :class:`~.QuantumProgram` with :class:`~.SamplexItem` objects for each pub,
        with ``passthrough data`` configured for
        :class:`~qiskit_ibm_runtime.executor_estimator.estimator.EstimatorV2` post-processing.

    Raises:
        IBMInputValueError: If pubs have mismatched precision,
            if a circuit contains mid-circuit measurements, or if a circuit already uses the
            reserved classical register name ``_meas``.
        IBMInputValueError: If ``noise_model_mapping`` is missing a noise map for at least one of
            the pubs layers.
    """
    if not twirling_options.enable_gates:
        raise ValueError("PEC requires enabling twirling for gates.")
    if measure_noise_learning is not None and not twirling_options.enable_measure:
        raise ValueError("Measure noise learning requires enabling twirling for measurements.")

    num_randomizations, shots_per_randomization = calculate_pec_twirling_shots(
        shots,
        twirling_options.num_randomizations,
        twirling_options.shots_per_randomization,
    )
    # Preserve the twirling randomization count: ``num_randomizations`` is scaled
    # per-pub by the PEC sampling overhead below, but the TREX calibration should
    # follow the (unscaled) twirling value.
    twirling_num_randomizations = num_randomizations

    # set max_overhead
    max_overhead = pec_options.max_overhead
    if max_overhead is None:
        # This is a backup max number of shots, intended to stop python
        # crashing with an overflow error if the noise is really strong
        max_overhead = sys.float_info.max / (num_randomizations * shots_per_randomization)

    # Create items
    items: list[SamplexItem] = []
    observables_list = []
    param_basis_pairs_list = []
    param_shapes_list = []
    pec_gamma_list = []

    pm_kwargs = options_to_boxing_pm_kwargs(
        twirling_options,
        measure_noise_learning,
        inject_noise=True,
        add_tags=add_tags,
    )
    for i, pub in enumerate(pubs):
        logger.info("Processing pub %d/%d", i + 1, len(pubs))

        boxed_circuit = box_circuit(circuit=pub.circuit, **pm_kwargs)

        # Build the template and the samplex
        template, samplex = build(boxed_circuit)

        # Prepare samplex_arguments
        flat_parameter_values, change_basis, param_basis_pairs = compute_samplex_arguments(pub)
        samplex_arguments = make_samplex_arguments(
            samplex, boxed_circuit, flat_parameter_values, change_basis
        )

        # add samplex_arguments related to noise injection
        if pec_options.noise_gain == "auto":
            # calculate the gamma factor without scaling it by noise_factor
            gamma = calculate_gamma(boxed_circuit, noise_model_mapping, 1)
            # calculate the noise factor based on gamma and max_overhead, setting it to ``1``
            # if ``gamma`` is ``1``--i.e., if there is no noise to mitigate.
            noise_gain = 1 if gamma == 1 else 1 - np.log(max_overhead) / np.log(gamma**2)
            # Truncate noise_gain to [0, 1]
            noise_gain = min(1, max(0, noise_gain))
        else:
            noise_gain = pec_options.noise_gain
        # noise_gain - the user facing parameter reflecting "how much noise remains after removal".
        # noise_scale - samplomatic parameter reflecting "how much noise is injected". The noise
        # is injected as quasi-probability and should be negative for removing noise (-1 is full
        # removal of the noise and 0 is no rescaling of the noise).
        # noise_factor - factor for scaled gamma calculation, reflecting the factor by which the
        # noise should be multiplied.

        # Adjusting noise_scale to [-1, 0] range from the [0, 1] range of noise_gain
        noise_scale = noise_gain - 1
        # The sampling scaling is proportional to 1 - noise_gain, as 0 is full PEC and 1 is no PEC
        noise_factor = 1 - noise_gain

        # Create a noise model map containing only the layers relevant for the current pub
        specs = samplex.inputs().get_specs("pauli_lindblad_maps")
        pub_noise_model = {}
        for spec in specs:
            ref = spec.name.split(".")[-1]
            try:
                pub_noise_model[ref] = noise_model_mapping[ref]
            except KeyError:
                raise IBMInputValueError(f"Noise model is missing for layer with reference {ref}")
            # noise_scales and pauli_lindblad_maps should have the same refs
            samplex_arguments[f"noise_scales.{ref}"] = noise_scale

        samplex_arguments["pauli_lindblad_maps"] = pub_noise_model
        scaled_gamma = calculate_gamma(boxed_circuit, pub_noise_model, noise_factor)
        pec_gamma_list.append(scaled_gamma)
        # Scale the amount of randomizations by gamma**2
        sampling_overhead = scaled_gamma**2
        num_randomizations = int(
            np.ceil(min(num_randomizations * max_overhead, num_randomizations * sampling_overhead))
        )

        # Create SamplexItem
        shape = (num_randomizations, change_basis.shape[0])
        items.append(
            SamplexItem(
                circuit=template,
                samplex=samplex,
                samplex_arguments=samplex_arguments,
                shape=shape,
            )
        )

        # Store data for passthrough
        observables_list.append(pub.observables.tolist())
        param_basis_pairs_list.append(param_basis_pairs)
        param_shapes_list.append(pub.parameter_values.shape)

    passthrough_data = {
        "post_processor": {
            "version": "v0.1",
            "circuits_metadata": [pub.circuit.metadata for pub in pubs],
            "observables": observables_list,
            "param_basis_pairs": param_basis_pairs_list,
            "param_shapes": param_shapes_list,
            "measure_mitigation": "False",
            "mitigation": "pec",
            "pec_gammas": pec_gamma_list,
        },
    }

    # Create QuantumProgram
    quantum_program = QuantumProgram(
        shots=shots_per_randomization,
        items=items,
        passthrough_data=passthrough_data,
    )

    # Add TREX calibration circuit
    if measure_noise_learning is not None:
        trex_num_randomizations = resolve_trex_num_randomizations(
            measure_noise_learning, twirling_num_randomizations
        )
        trex_item = create_trex_calibration_circuit(pubs, trex_num_randomizations)
        quantum_program.items.append(trex_item)
        passthrough_data["post_processor"]["measure_mitigation"] = "True"

    # Set semantic role for post-processing dispatch
    quantum_program._semantic_role = "estimator_v2"

    return quantum_program
