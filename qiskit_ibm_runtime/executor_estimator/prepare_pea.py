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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from qiskit.quantum_info import PauliLindbladMap

    from ..options_models.measure_noise_learning_options import MeasureNoiseLearningOptions
    from ..options_models.twirling_options import TwirlingOptions
    from ..options_models.zne_options import ZneOptions

import numpy as np
from samplomatic import build

from ..exceptions import IBMInputValueError
from ..executor.calculate_twirling_shots import calculate_twirling_shots
from ..options_models.zne_options import PEA_DEFAULT_NOISE_FACTORS
from ..quantum_program import QuantumProgram
from ..quantum_program.quantum_program import SamplexItem
from .trex_utils import create_trex_calibration_circuit, resolve_trex_num_randomizations
from .utils import (
    box_circuit,
    compute_samplex_arguments,
    make_samplex_arguments,
    options_to_boxing_pm_kwargs,
)

logger = logging.getLogger(__name__)


def prepare_pea(
    pubs: Sequence[EstimatorPub],
    twirling_options: TwirlingOptions,
    shots: int,
    zne_options: ZneOptions,
    noise_model_mapping: dict[str, PauliLindbladMap],
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
    add_tags: bool = False,
) -> QuantumProgram:
    """Convert estimator PUBs to a quantum program.

    Args:
        pubs: List of estimator pubs to convert.
        twirling_options: The twirling options.
        shots: The number of shots to use. Will be overridden by
            ``num_randomizations * shots_per_randomization`` when both are specified explicitly
            and twirling is on.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be used.
        zne_options: The options for PEA mitigation (which have the same options as ZNE).
        noise_model_mapping: Mapping between layer ref to a noise model to use for noise
            amplification. The dict contains layers from all pubs. Assumes that the unique
            layers used for noise learning were extracted using the ``find_unique_layers`` method.
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
        IBMInputValueError: If noise_model_mapping is missing a noise map for at least one of
            the pubs layers.

    """
    if not twirling_options.enable_gates:
        raise ValueError("PEA requires enabling twirling for gates.")
    if measure_noise_learning is not None and not twirling_options.enable_measure:
        raise ValueError("Measure noise learning requires enabling twirling for measurements.")
    if zne_options.amplifier != "pea":
        raise IBMInputValueError("PEA mitigation must be used with ``pea`` as noise amplification.")

    if zne_options.noise_factors == "auto":
        noise_factors = np.array(PEA_DEFAULT_NOISE_FACTORS)
    else:
        noise_factors = np.array(zne_options.noise_factors)

    num_randomizations, shots_per_randomization = calculate_twirling_shots(
        shots,
        twirling_options.num_randomizations,
        twirling_options.shots_per_randomization,
    )

    # Create items
    items: list[SamplexItem] = []
    observables_list = []
    param_basis_pairs_list = []
    param_shapes_list = []

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
        # make parameters array broadcastable with the noise scales
        flat_parameter_values = np.expand_dims(flat_parameter_values, 0)
        samplex_arguments = make_samplex_arguments(
            samplex, boxed_circuit, flat_parameter_values, change_basis
        )

        # add samplex_arguments related to noise injection

        # Subtract 1 from noise_factors, since a value of 1 represents the noise
        # that is present in the circuit in the absence of amplification.
        # Also, make noise_scales broadcastable with the parameters.
        noise_scales = np.expand_dims(np.array(noise_factors) - 1, -1)

        # Create a noise model map containing only the layers relevant for the current pub
        specs = samplex.inputs().get_specs("pauli_lindblad_maps")
        pub_noise_model = {}
        for spec in specs:
            ref = spec.name.split(".")[-1]
            if ref not in noise_model_mapping.keys():
                raise IBMInputValueError(
                    f"noise_model_mapping is missing noise map for layer reference {ref}"
                )
            pub_noise_model[ref] = noise_model_mapping[ref]
            samplex_arguments[f"noise_scales.{ref}"] = noise_scales

        samplex_arguments["pauli_lindblad_maps"] = pub_noise_model

        # Create SamplexItem
        shape = (num_randomizations, len(noise_scales), change_basis.shape[0])
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
            "mitigation": "pea",
            "circuits_metadata": [pub.circuit.metadata for pub in pubs],
            "observables": observables_list,
            "param_basis_pairs": param_basis_pairs_list,
            "param_shapes": param_shapes_list,
            "measure_mitigation": measure_noise_learning is not None,
            "pea_noise_factors": noise_factors,
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
        if (
            isinstance(measure_noise_learning.shots_per_randomization, int)
            and measure_noise_learning.shots_per_randomization != shots_per_randomization
        ):
            raise IBMInputValueError(
                "shots_per_randomization must be the same for twirling and measure_noise_learning"
            )
        trex_num_randomizations = resolve_trex_num_randomizations(
            measure_noise_learning, num_randomizations
        )
        trex_item = create_trex_calibration_circuit(pubs, trex_num_randomizations)
        quantum_program.items.append(trex_item)
        passthrough_data["post_processor"]["measure_mitigation"] = "True"

    # Set semantic role for post-processing dispatch
    quantum_program._semantic_role = "estimator_v2"

    return quantum_program
