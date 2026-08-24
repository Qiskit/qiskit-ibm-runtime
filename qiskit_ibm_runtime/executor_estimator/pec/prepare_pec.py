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

    from ...options_models.measure_noise_learning import MeasureNoiseLearningOptions
    from ...options_models.pec import PecOptions
    from ...options_models.twirling import TwirlingOptions

from qiskit_mitigation.pec import PEC

from ...quantum_program import QuantumProgram
from ..utils import options_to_boxing_pm_kwargs
from .utils import calculate_pec_twirling_shots

logger = logging.getLogger(__name__)


def prepare_pec(
    pubs: Sequence[EstimatorPub],
    twirling_options: TwirlingOptions,
    shots: int,
    pec_options: PecOptions,
    noise_model: dict[str, PauliLindbladMap],
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
    add_tags: bool = False,
) -> QuantumProgram:
    """Convert estimator PUBs to a quantum program with PEC mitigation applied.

    Args:
        pubs: List of estimator pubs to convert.
        twirling_options: The twirling options.
        shots: The number of pre-overhead shots to use. Will be overridden by
            ``num_randomizations * shots_per_randomization`` when both are specified explicitly.
            The number of shots of each pub will be multiplied by the sampling overhead of gamma^2.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be used.
        pec_options: The options for PEC mitigation.
        noise_model: Mapping between layer ref to a noise model to use for PEC mitigation
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
        IBMInputValueError: If ``noise_model`` is missing a noise map for at least one of
            the pubs layers.
    """
    if not twirling_options.enable_gates:
        raise ValueError("PEC requires enabling twirling for gates.")
    if measure_noise_learning is not None and not twirling_options.enable_measure:
        raise ValueError("Measure noise learning requires enabling twirling for measurements.")

    baseline_num_randomizations, shots_per_randomization = calculate_pec_twirling_shots(
        shots,
        twirling_options.num_randomizations,
        twirling_options.shots_per_randomization,
    )

    # set max_overhead
    max_overhead = pec_options.max_overhead
    if max_overhead is None:
        # This is a backup max number of shots, intended to stop python
        # crashing with an overflow error if the noise is really strong
        max_overhead = sys.float_info.max / (baseline_num_randomizations * shots_per_randomization)

    pec = PEC()
    qp = QuantumProgram(shots=shots_per_randomization)

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

    custom_options = {
        "enable_gates": pm_kwargs["enable_gates"],
        "enable_measures": True,
        "twirling_strategy": pm_kwargs["twirling_strategy"],
        "twirling_group": pm_kwargs["twirling_group"],
        "measure_annotations": pm_kwargs["measure_annotations"],
        "inject_noise_site": "after",
        "inject_noise_targets": "gates" if pm_kwargs["inject_noise"] else "none",
        "inject_noise_strategy": "uniform_modification"
        if pm_kwargs["inject_noise"]
        else "no_modification",
        "add_tags": pm_kwargs["add_tags"],
    }

    for i, pub in enumerate(pubs):
        logger.info("Processing pub %d/%d", i + 1, len(pubs))
        pec.prepare(
            pub.circuit,
            pub.observables,
            pub.parameter_values,
            custom_options,
            shots_per_randomization=shots_per_randomization,
            num_randomizations=baseline_num_randomizations,
            quantum_program=qp,
            noise_maps=noise_model,
            noise_gain=pec_options.noise_gain,
            max_sampling_overhead=max_overhead,
        )
        # Store data for passthrough
        observables_list.append(pub.observables.tolist())
        param_basis_pairs_list.append(pec.param_basis_pairs)
        param_shapes_list.append(pub.parameter_values.shape)
        pec_gamma_list.append(pec.gamma)

    passthrough_data = {
        "post_processor": {
            "version": "v0.1",
            "circuits_metadata": [pub.circuit.metadata for pub in pubs],
            "observables": observables_list,
            "param_basis_pairs": param_basis_pairs_list,
            "param_shapes": param_shapes_list,
            "measure_mitigation": False,
            "mitigation": "pec",
            "pec_gammas": pec_gamma_list,
        },
    }

    qp.passthrough_data = passthrough_data

    return qp
