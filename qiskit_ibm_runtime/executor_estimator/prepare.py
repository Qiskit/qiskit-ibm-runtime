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

import numpy as np
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from ..exceptions import IBMInputValueError
from ..executor.dynamical_decoupling import apply_dynamical_decoupling
from ..options_models.converters import estimator_options_to_executor_options
from ..utils.utils import validate_no_boxes
from .finalize_options import finalize_estimator_options
from .pec.prepare_pec import prepare_pec
from .prepare_pea import prepare_pea
from .prepare_vanilla import prepare_vanilla
from .utils import resolve_precision
from .zne.prepare_zne import prepare_zne

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.primitives.containers.estimator_pub import EstimatorPubLike
    from qiskit.providers import BackendV2

    from ..options_models.estimator import EstimatorOptions
    from ..options_models.executor import ExecutorOptions
    from ..quantum_program import QuantumProgram


logger = logging.getLogger(__name__)


def prepare(
    pubs: Iterable[EstimatorPubLike],
    options: EstimatorOptions,
    precision: float | None = None,
    add_tags: bool = False,
    backend: BackendV2 | None = None,
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a sequence of estimator PUBs to a quantum program and map options.

    This method processes estimator PUBs (Primitive Unified Blocs) and converts them into
    a :class:`~.QuantumProgram` suitable for execution, along with the corresponding
    :class:`~.ExecutorOptions`.

    Args:
        pubs: Iterable of PUB-like objects to convert.
        options: The estimator options.
        precision: The target precision for expectation value estimates of each estimator pub
            that does not specify its own precision. If ``None``, the value from
            ``options.default_precision`` or ``options.default_shots`` will be used.
        add_tags: Whether to include tags for the boxes. ``False`` will cause no tags to be added
            (will pass the ``"none"`` value to the relevant attribute), while ``True`` will cause
            tags with the twirled boxes hash to be added (using the ``"unique_box"`` value of the
            relevant attribute). These tags are used to inject noise when running in local mode.
        backend: The backend for which the program is prepared. Only required when dynamical
            decoupling is enabled.

    Returns:
        A tuple containing:

        - :class:`~.QuantumProgram` with :class:`~.CircuitItem` or :class:`~.SamplexItem`
            objects for each pub, with ``passthrough_data`` fully populated for post-processing.
        - :class:`~.ExecutorOptions` mapped from the finalized estimator options.

    Raises:
        IBMInputValueError: If no pubs are provided, if precision is not properly specified,
            or if unsupported option combinations are detected.
    """
    # Coerce PUBs
    coerced_pubs = [EstimatorPub.coerce(pub, precision) for pub in pubs]
    if not coerced_pubs:
        raise IBMInputValueError("No pubs provided. At least one pub is required.")

    # Finalize options (resilience-level defaults + dependency enforcement)
    finalized_options = finalize_estimator_options(options)

    # Resolve shots
    resolved_precision = resolve_precision(coerced_pubs, precision)
    if resolved_precision is not None:
        shots = int(np.ceil(1.0 / (resolved_precision**2)))
    elif finalized_options.default_shots is not None:
        shots = int(finalized_options.default_shots)
    else:
        shots = int(np.ceil(1.0 / (finalized_options.default_precision**2)))

    if finalized_options.resilience.pec_mitigation and finalized_options.resilience.zne_mitigation:
        raise IBMInputValueError(
            "PEC mitigation and ZNE mitigation are incompatible with one another."
        )

    for pub in coerced_pubs:
        validate_no_boxes(pub.circuit)

        if finalized_options.dynamical_decoupling.enable:
            if pub.circuit.has_control_flow_op():
                raise IBMInputValueError(
                    "Dynamical decoupling is not compatible with dynamic circuits "
                    "(circuits with control flow operations)."
                )
            if backend is None:
                raise IBMInputValueError(
                    "A backend must be provided when dynamical decoupling is enabled."
                )

    executor_options = estimator_options_to_executor_options(finalized_options)

    if finalized_options.resilience.pec_mitigation:
        logger.info("Running ``prepare_pec``.")
        quantum_program = prepare_pec(
            pubs=coerced_pubs,
            twirling_options=finalized_options.twirling,
            shots=shots,
            pec_options=finalized_options.resilience.pec,
            noise_model=finalized_options.resilience.noise_model,
            measure_noise_learning=finalized_options.resilience.measure_noise_learning
            if finalized_options.resilience.measure_mitigation
            else None,
            add_tags=add_tags,
        )
    elif finalized_options.resilience.zne_mitigation:
        if finalized_options.resilience.zne.amplifier == "pea":
            logger.info("Running ``prepare_pea``.")
            quantum_program = prepare_pea(
                pubs=coerced_pubs,
                twirling_options=finalized_options.twirling,
                shots=shots,
                zne_options=finalized_options.resilience.zne,
                noise_model=finalized_options.resilience.noise_model,
                measure_noise_learning=finalized_options.resilience.measure_noise_learning
                if finalized_options.resilience.measure_mitigation
                else None,
                add_tags=add_tags,
            )
        else:
            logger.info("Running ``prepare_zne``.")
            quantum_program = prepare_zne(
                pubs=coerced_pubs,
                twirling_options=finalized_options.twirling,
                shots=shots,
                zne_options=finalized_options.resilience.zne,
                measure_noise_learning=finalized_options.resilience.measure_noise_learning
                if finalized_options.resilience.measure_mitigation
                else None,
                add_tags=add_tags,
            )
    else:
        logger.info("Running ``prepare_vanilla``.")
        quantum_program = prepare_vanilla(
            pubs=coerced_pubs,
            twirling_options=finalized_options.twirling,
            shots=shots,
            measure_noise_learning=finalized_options.resilience.measure_noise_learning
            if finalized_options.resilience.measure_mitigation
            else None,
            add_tags=add_tags,
        )
    if finalized_options.dynamical_decoupling.enable:
        logger.info("Apply dynamical decoupling")
        quantum_program = apply_dynamical_decoupling(
            backend=backend,
            dd_options=finalized_options.dynamical_decoupling,
            quantum_program=quantum_program,
        )

    # Annotate passthrough_data for post-processing
    quantum_program.passthrough_data["post_processor"]["options"] = finalized_options.model_dump(  # type: ignore[index, call-overload]
        exclude={"resilience": {"noise_model"}}
    )
    quantum_program.passthrough_data["post_processor"]["shots"] = shots  # type: ignore[index, call-overload]
    quantum_program.passthrough_data["post_processor"]["precision"] = resolved_precision  # type: ignore[index, call-overload]

    return quantum_program, executor_options
