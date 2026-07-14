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

"""Prepare function for Executor-based EstimatorV2 primitive."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub

    from ...options_models.measure_noise_learning_options import MeasureNoiseLearningOptions
    from ...options_models.twirling_options import TwirlingOptions
    from ...options_models.zne_options import ZneOptions

import numpy as np
from qiskit.transpiler import PassManager
from samplomatic import build

from ...exceptions import IBMInputValueError
from ...executor.calculate_twirling_shots import calculate_twirling_shots
from ...options_models.zne_options import ZNE_DEFAULT_NOISE_FACTORS
from ...quantum_program import QuantumProgram
from ...quantum_program.quantum_program import SamplexItem
from ..trex_utils import create_trex_calibration_circuit, resolve_trex_num_randomizations
from ..utils import (
    box_circuit,
    compute_samplex_arguments,
    make_samplex_arguments,
    options_to_boxing_pm_kwargs,
)
from .gate_folding import GateFolding

logger = logging.getLogger(__name__)


def prepare_zne(
    pubs: Sequence[EstimatorPub],
    twirling_options: TwirlingOptions,
    shots: int,
    zne_options: ZneOptions,
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
        zne_options: The options for ZNE mitigation.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be used.
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
        IBMInputValueError: If the amplifier in the ZneOptions is not one of ``gate_folding``,
        ``gate_folding_front`` or ``gate_folding_back``.
    """
    if measure_noise_learning is not None and not twirling_options.enable_measure:
        raise ValueError("Measure noise learning requires enabling twirling for measurements.")
    if zne_options.amplifier not in ["gate_folding", "gate_folding_front", "gate_folding_back"]:
        raise IBMInputValueError(
            "ZNE mitigation must be used with a gate folding noise amplification."
        )

    if zne_options.noise_factors == "auto":
        noise_factors = np.array(ZNE_DEFAULT_NOISE_FACTORS)
    else:
        noise_factors = np.array(zne_options.noise_factors)

    if twirling_options.enable_gates or twirling_options.enable_measure:
        num_randomizations, shots_per_randomization = calculate_twirling_shots(
            shots,
            twirling_options.num_randomizations,
            twirling_options.shots_per_randomization,
        )
    else:
        num_randomizations = 1
        shots_per_randomization = shots

    # Create items
    items: list[SamplexItem] = []
    observables_list = []
    param_basis_pairs_list = []
    param_shapes_list = []
    item_id = []

    pm_kwargs = options_to_boxing_pm_kwargs(
        twirling_options,
        measure_noise_learning,
        inject_noise=False,
        add_tags=add_tags,
    )
    for i, pub in enumerate(pubs):
        logger.info("Processing pub %d/%d", i + 1, len(pubs))

        # Prepare samplex_arguments that are common to all noise factors
        flat_parameter_values, change_basis, param_basis_pairs = compute_samplex_arguments(pub)

        for j, noise_factor in enumerate(noise_factors):
            logger.info("Processing noise factor %d/%d", j + 1, len(noise_factors))

            folding_method: Literal["random", "front", "back"]
            match zne_options.amplifier:
                case "gate_folding":
                    folding_method = "random"
                case "gate_folding_front":
                    folding_method = "front"
                case "gate_folding_back":
                    folding_method = "back"
                case _:
                    # This should never happen due to prior validation
                    folding_method = "random"

            folding_pm = PassManager([GateFolding(noise_factor, folding_method)])
            folded_circuit = folding_pm.run(pub.circuit)

            boxed_circuit = box_circuit(circuit=folded_circuit, **pm_kwargs)

            # Build the template and the samplex
            template, samplex = build(boxed_circuit)

            # Prepare samplex_arguments for the current noise factor
            samplex_arguments = make_samplex_arguments(
                samplex, boxed_circuit, flat_parameter_values, change_basis
            )

            # Create SamplexItem
            # Each pub will have len(noise_factors) associated items
            shape = (num_randomizations, change_basis.shape[0])
            items.append(
                SamplexItem(
                    circuit=template,
                    samplex=samplex,
                    samplex_arguments=samplex_arguments,
                    shape=shape,
                )
            )

            # each index is the item index, and it maps to (pub_number, noise_factor)
            item_id.append((i, noise_factor))

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
            "measure_mitigation": measure_noise_learning is not None,
            "mitigation": "zne",
            "zne_noise_factors": noise_factors,
            "item_id": item_id,
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
