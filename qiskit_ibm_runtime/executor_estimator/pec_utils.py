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

    from qiskit import QuantumCircuit
    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from qiskit.quantum_info import PauliLindbladMap

    from ..options_models.measure_noise_learning_options import MeasureNoiseLearningOptions
    from ..options_models.pec_options import PecOptions
    from ..options_models.twirling_options import TwirlingOptions

import numpy as np
from samplomatic import InjectNoise, build
from samplomatic.utils import get_annotation

from ..exceptions import IBMInputValueError
from ..executor.calculate_twirling_shots import calculate_twirling_shots
from ..quantum_program import QuantumProgram
from ..quantum_program.datatree import is_datatree_compatible
from ..quantum_program.quantum_program import SamplexItem
from .prepare import box_circuit, build_basic_samplex_args, compute_samplex_arguments
from .trex_utils import create_trex_calibration_circuit

logger = logging.getLogger(__name__)


def calculate_gamma(
    boxed_circuit: QuantumCircuit,
    noise_model_mapping: dict[str, PauliLindbladMap],
    noise_factor: float,
) -> float:
    """Calculate the PEC gamma factor of a circuit based on a noise model.

    The returned gamma is that associated with the inverse noise maps needed
    to cancel the noise in the circuit.

    Args:
        boxed_circuit: The annotated circuit to calculate the PEC gamma for.
        noise_model_mapping: Mapping between layer ref to a noise model
        noise_factor: The noise factor of the noise amplification.

    Returns:
        The PEC gamma factor.
    """
    gamma = 1.0
    for instr in boxed_circuit:
        if annot := get_annotation(instr.operation, InjectNoise):
            plm = noise_model_mapping[annot.ref]
            # scale the noise by noise_factor
            plm = plm.scale_rates(noise_factor)
            gamma *= plm.inverse().gamma()
    return gamma


def prepare_pec(
    pubs: Sequence[EstimatorPub],
    twirling_options: TwirlingOptions,
    shots: int,
    pec_options: PecOptions,
    noise_model_mapping: Sequence[dict[str, PauliLindbladMap]],
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
) -> QuantumProgram:
    """Convert estimator PUBs to a quantum program with PEC mitigation.

    Args:
        pubs: List of estimator pubs to convert.
        twirling_options: The twirling options.
        shots: The number of shots to use. Will be overridden by
            ``num_randomizations * shots_per_randomization`` when both are specified explicitly
            and twirling is on.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be used.
        pec_options: The options for PEC mitigation.
        noise_model_mapping: List of mapping between layer ref to a noise model to use for PEC or
            PEA mitigation methods. The list must contain a map for each pub. Assumes that the
            unique layers used for noise learning were extracted using the ``get_layers`` method.

    Returns:
        :class:`~.QuantumProgram` with :class:`~.SamplexItem` objects for each pub,
        with ``passthrough data`` configured for
        :class:`~qiskit_ibm_runtime.executor_estimator.estimator.EstimatorV2` post-processing.

    Raises:
        IBMInputValueError: If pubs have mismatched precision,
            if a circuit contains mid-circuit measurements, or if a circuit already uses the
            reserved classical register name ``_meas``.
        IBMInputValueError: If the length of noise_model_mapping and the length of the pubs
            mismatched.
    """
    if twirling_options.enable_gates or twirling_options.enable_measure:
        num_randomizations, shots_per_randomization = calculate_twirling_shots(
            shots,
            twirling_options.num_randomizations,
            twirling_options.shots_per_randomization,
        )
    else:
        num_randomizations = 1
        shots_per_randomization = shots

    # validate noise_model_mapping length
    if noise_model_mapping is None or (
        noise_model_mapping is not None and len(noise_model_mapping) != len(pubs)
    ):
        raise IBMInputValueError(
            "If PEC mitigation is used, the input must contain noise_model_mapping for each pub"
        )

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

    for i, pub in enumerate(pubs):
        logger.info("Processing pub %d/%d", i + 1, len(pubs))

        boxed_circuit = box_circuit(
            pub.circuit, twirling_options, measure_noise_learning, pec_options
        )

        # Build the template and the samplex
        template, samplex = build(boxed_circuit)

        # Prepare samplex_arguments
        flat_parameter_values, change_basis, param_basis_pairs = compute_samplex_arguments(pub)
        samplex_arguments = build_basic_samplex_args(
            samplex, boxed_circuit, flat_parameter_values, change_basis
        )

        # add samplex_arguments related to noise injection
        if pec_options.noise_gain == "auto":
            scaleless_gamma = calculate_gamma(boxed_circuit, noise_model_mapping[i], 1)
            noise_gain = 1 - np.log(max_overhead) / np.log(scaleless_gamma**2)
            # Truncate noise_gain to [0, 1]
            noise_gain = min(1, max(0, noise_gain))
        else:
            noise_gain = pec_options.noise_gain
        # in samplomatic -1 is full removal of the noise and 0 is no rescaling of the noise
        noise_scale = noise_gain - 1
        # The sampling scaling is proportional to 1 - noise_gain, as 0 is full PEC and 1 is no PEC
        noise_factor = 1 - noise_gain
        for ref in noise_model_mapping[i]:
            samplex_arguments[f"noise_scales.{ref}"] = noise_scale
        samplex_arguments["pauli_lindblad_maps"] = noise_model_mapping[i]
        scaled_gamma = calculate_gamma(boxed_circuit, noise_model_mapping[i], noise_factor)
        pec_gamma_list.append(scaled_gamma)
        # Scale the amount of randomizations by gamma**2
        sampling_overhead = scaled_gamma**2
        num_randomizations = 1 if num_randomizations == 0 else num_randomizations
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

    # Collect circuit metadata from each pub
    circuits_metadata = [pub.circuit.metadata for pub in pubs]

    # Validate that circuit metadata is compatible with DataTree format
    for idx, metadata in enumerate(circuits_metadata):
        if metadata is not None and not is_datatree_compatible(metadata):
            raise IBMInputValueError(
                f"Circuit metadata at index {idx} is not compatible with DataTree format. "
                f"Metadata must be a nested structure of lists, dicts (with string keys), "
                f"numpy arrays, or primitive types (str, int, float, bool, None)."
            )

    passthrough_data = {
        "post_processor": {
            "version": "v0.1",
            "circuits_metadata": circuits_metadata,
            "observables": observables_list,
            "param_basis_pairs": param_basis_pairs_list,
            "param_shapes": param_shapes_list,
            "measure_mitigation": "False",
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
        if (
            isinstance(measure_noise_learning.shots_per_randomization, int)
            and measure_noise_learning.shots_per_randomization != shots_per_randomization
        ):
            raise IBMInputValueError(
                "shots_per_randomization must be the same for twirling and measure_noise_learning"
            )
        trex_item = create_trex_calibration_circuit(pubs, measure_noise_learning)
        quantum_program.items.append(trex_item)
        passthrough_data["post_processor"]["measure_mitigation"] = "True"

    # Set semantic role for post-processing dispatch
    quantum_program._semantic_role = "estimator_v2"

    return quantum_program
