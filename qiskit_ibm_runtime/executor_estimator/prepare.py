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
from typing import TYPE_CHECKING

from ..exceptions import IBMInputValueError
from ..executor.dynamical_decoupling import apply_dynamical_decoupling
from ..options_models.converters import estimator_options_to_executor_options
from .pec.prepare_pec import prepare_pec
from .prepare_pea import prepare_pea
from .prepare_vanilla import prepare_vanilla
from .zne.prepare_zne import prepare_zne

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from qiskit.providers import BackendV2

    from ..options_models.estimator import EstimatorOptions
    from ..options_models.executor import ExecutorOptions
    from ..quantum_program import QuantumProgram


logger = logging.getLogger(__name__)


def prepare(
    pubs: Sequence[EstimatorPub],
    options: EstimatorOptions,
    shots: int | None = None,
    add_tags: bool = False,
    backend: BackendV2 | None = None,
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a sequence of estimator PUBs to a quantum program and map options.

    This method processes estimator PUBs (Primitive Unified Blocs) and converts them into
    a :class:`~.QuantumProgram` suitable for execution, along with the corresponding
    :class:`~.ExecutorOptions`.

    Args:
        pubs: List of estimator PUBs to convert.
        options: The options.
        shots: The number of shots to use. Will be overridden by
            ``num_randomizations * shots_per_randomization`` when both are specified explicitly
            and twirling is on.
        add_tags: Whether to include tags for the boxes. Relevant mainly for debugging.
            ``False`` will cause no tags to be added (will pass the "none" value to the relevant
            attribute), while ``True`` will cause tags with the twirled boxes hash to be added
            (using the "unique_box" value of the relevant attribute). These tags can help
            injecting noise in simulators.
        backend: The backend for which the program is prepared. Only required when dynamical
            decoupling is enabled.

    Returns:
        A tuple containing:

        - :class:`~.QuantumProgram` with :class:`~.CircuitItem` or :class:`~.SamplexItem`
            objects for each pub, with passthrough_data configured for post-processing.
        - :class:`~.ExecutorOptions` mapped from the estimator's options.
    """
    if options.dynamical_decoupling.enable:
        for pub in pubs:
            if pub.circuit.has_control_flow_op():
                raise IBMInputValueError(
                    "Dynamical decoupling is not compatible with dynamic circuits "
                    "(circuits with control flow operations)."
                )
        if backend is None:
            raise IBMInputValueError(
                "A backend must be provided when dynamical decoupling is enabled."
            )

    # Map options to executor options
    executor_options = estimator_options_to_executor_options(options)

    if options.resilience.pec_mitigation:
        logger.info("Running ``prepare_pec``.")
        quantum_program = prepare_pec(
            pubs=pubs,
            twirling_options=options.twirling,
            shots=shots,
            pec_options=options.resilience.pec,
            noise_model_mapping=options.resilience.noise_model_mapping,
            measure_noise_learning=options.resilience.measure_noise_learning
            if options.resilience.measure_mitigation
            else None,
            add_tags=add_tags,
        )
    elif options.resilience.zne_mitigation:
        if options.resilience.zne.amplifier == "pea":
            logger.info("Running ``prepare_pea``.")
            quantum_program = prepare_pea(
                pubs=pubs,
                twirling_options=options.twirling,
                shots=shots,
                zne_options=options.resilience.zne,
                noise_model_mapping=options.resilience.noise_model_mapping,
                measure_noise_learning=options.resilience.measure_noise_learning
                if options.resilience.measure_mitigation
                else None,
                add_tags=add_tags,
            )
        else:
            logger.info("Running ``prepare_zne``.")
            quantum_program = prepare_zne(
                pubs=pubs,
                twirling_options=options.twirling,
                shots=shots,
                zne_options=options.resilience.zne,
                measure_noise_learning=options.resilience.measure_noise_learning
                if options.resilience.measure_mitigation
                else None,
                add_tags=add_tags,
            )
    else:
        logger.info("Running ``prepare_vanilla``.")
        quantum_program = prepare_vanilla(
            pubs=pubs,
            twirling_options=options.twirling,
            shots=shots,
            measure_noise_learning=options.resilience.measure_noise_learning
            if options.resilience.measure_mitigation
            else None,
            add_tags=add_tags,
        )
    if options.dynamical_decoupling.enable:
        logger.info("Apply dynamical decoupling")
        quantum_program = apply_dynamical_decoupling(
            backend=backend,
            dd_options=options.dynamical_decoupling,
            quantum_program=quantum_program,
        )

    return quantum_program, executor_options
