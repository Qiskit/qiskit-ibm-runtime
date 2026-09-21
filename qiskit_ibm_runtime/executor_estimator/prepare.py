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

"""Prepare function for client-side Estimator primitive."""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING

import numpy as np
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit_mitigation import PEA, PEC, TREX, GateFolding, MitigationTask
from samplomatic.annotations import InjectNoise
from samplomatic.utils import get_annotation

from ..exceptions import IBMInputValueError
from ..executor.calculate_twirling_shots import calculate_twirling_shots
from ..executor.dynamical_decoupling import apply_dynamical_decoupling
from ..options_models.converters import estimator_options_to_executor_options
from ..quantum_program import QuantumProgram
from ..utils.utils import validate_no_boxes
from .finalize_options import finalize_estimator_options
from .options_to_mitigation import estimator_options_to_boxing_options
from .pec_utils import calculate_pec_twirling_shots, resolve_pec_max_overhead
from .trex_setup import apply_trex
from .utils import (
    has_projection_operators,
    resolve_noise_factors,
    resolve_precision,
    validate_noise_factors,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPubLike
    from qiskit.providers import BackendV2

    from ..options_models.estimator import EstimatorOptions
    from ..options_models.executor import ExecutorOptions
    from ..options_models.resilience import ResilienceOptions

logger = logging.getLogger(__name__)

# Maps the user-facing ZNE amplifier name to qiskit-mitigation's folding_method string.
_ZNE_FOLDING_METHOD: dict[str, str] = {
    "gate_folding": "random",
    "gate_folding_front": "front",
    "gate_folding_back": "back",
}


def prepare(
    pubs: Iterable[EstimatorPubLike],
    options: EstimatorOptions,
    precision: float | None = None,
    add_tags: bool = False,
    backend: BackendV2 | None = None,
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a sequence of estimator PUBs to a quantum program and map options.

    Args:
        pubs: Iterable of PUB-like objects to convert.
        options: The estimator options.
        precision: The target precision for expectation value estimates of each estimator pub
            that does not specify its own precision. If ``None``, the value from
            ``options.default_precision`` or ``options.default_shots`` will be used.
        add_tags: Whether to include tags for the boxes.
        backend: The backend for which the program is prepared. Only required when dynamical
            decoupling is enabled.

    Returns:
        A tuple of a :class:`~.QuantumProgram` and :class:`~.ExecutorOptions`.

    Raises:
        IBMInputValueError: If no pubs are provided, if precision is not properly specified,
            or if unsupported option combinations are detected.
    """
    coerced_pubs = [EstimatorPub.coerce(pub, precision) for pub in pubs]
    finalized_options = finalize_estimator_options(options)

    if add_tags and finalized_options.resilience.measure_mitigation:
        warnings.warn(
            "Simulating estimation jobs with measure mitigation is not yet supported; "
            "measure mitigation will not be applied to the results."
        )

    _validate(coerced_pubs, finalized_options, backend)

    executor_options = estimator_options_to_executor_options(finalized_options)

    resolved_precision = resolve_precision(coerced_pubs, precision)
    if resolved_precision is not None:
        shots = int(np.ceil(1.0 / (resolved_precision**2)))
    elif finalized_options.default_shots is not None:
        shots = int(finalized_options.default_shots)
    else:
        shots = int(np.ceil(1.0 / (finalized_options.default_precision**2)))

    quantum_program = _build_quantum_program(
        coerced_pubs, finalized_options, shots, add_tags, backend
    )

    # Annotate our own metadata block (separate namespace from qiskit_mitigation)
    quantum_program.passthrough_data["post_processor"] = {  # type: ignore[index]
        "version": "v0.1",
        "options": finalized_options.model_dump(exclude={"resilience": {"layer_noise_model"}}),
        "shots": shots,
        "precision": resolved_precision,
        "circuits_metadata": [pub.circuit.metadata for pub in coerced_pubs],
        "num_pubs": len(coerced_pubs),
    }

    return quantum_program, executor_options


def _validate(
    coerced_pubs: Sequence[EstimatorPub],
    finalized_options: EstimatorOptions,
    backend: BackendV2 | None,
) -> None:
    """Validate the coerced pubs and finalized options.

    Args:
        coerced_pubs: The coerced estimator pubs.
        finalized_options: The finalized estimator options.
        backend: The backend for which the program is prepared.

    Raises:
        IBMInputValueError: If no pubs are provided.
        IBMInputValueError: If both PEC and ZNE mitigation are enabled simultaneously.
        IBMInputValueError: If PEA or PEC mitigation is requested without a noise model.
        IBMInputValueError: If the ZNE noise factors are insufficient for the requested
            extrapolator(s).
        IBMInputValueError: If measurement mitigation is used with observables that contain
            projection operators.
        IBMInputValueError: If dynamical decoupling is enabled on a circuit with control
            flow operations, or if no backend is provided when it is enabled.
    """
    if not coerced_pubs:
        raise IBMInputValueError("No pubs provided. At least one pub is required.")
    if finalized_options.resilience.pec_mitigation and finalized_options.resilience.zne_mitigation:
        raise IBMInputValueError(
            "PEC mitigation and ZNE mitigation are incompatible with one another."
        )

    resilience = finalized_options.resilience

    needs_noise_injection = resilience.pec_mitigation or (
        resilience.zne_mitigation and resilience.zne.amplifier == "pea"
    )
    if needs_noise_injection and resilience.layer_noise_model is None:
        raise IBMInputValueError(
            "PEA/PEC mitigation requires a noise model. "
            "Set 'resilience.layer_noise_model' before running."
        )

    if resilience.zne_mitigation:
        zne_options = resilience.zne
        # Validate noise_factors has enough points for every requested extrapolator.
        noise_factors, _ = resolve_noise_factors(zne_options)
        validate_noise_factors(noise_factors, normalise_extrapolator(zne_options.extrapolator))

    for pub in coerced_pubs:
        validate_no_boxes(pub.circuit)
        if finalized_options.resilience.measure_mitigation and has_projection_operators(pub):
            raise IBMInputValueError(
                "Measurement mitigation is currently not supported when observables contain "
                "projection operators. You can decompose into pauli operators if the "
                "exponential cost is acceptable."
            )
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


def choose_task_class(resilience: ResilienceOptions) -> type[MitigationTask]:
    """Return the qiskit-mitigation task class for the given resilience options."""
    if resilience.pec_mitigation:
        return PEC
    if resilience.zne_mitigation and resilience.zne.amplifier == "pea":
        return PEA
    if resilience.zne_mitigation:
        return GateFolding
    return MitigationTask


def _build_quantum_program(
    coerced_pubs: Sequence[EstimatorPub],
    finalized_options: EstimatorOptions,
    shots: int,
    add_tags: bool,
    backend: BackendV2 | None,
) -> QuantumProgram:
    """Build the :class:`~.QuantumProgram` for all pubs using the resolved mitigation pathway.

    Args:
        coerced_pubs: The coerced estimator pubs to process.
        finalized_options: The fully resolved estimator options.
        shots: The resolved shots.
        add_tags: Whether to include box tags.
        backend: Backend required when dynamical decoupling is enabled; ``None`` otherwise.

    Returns:
        A :class:`~.QuantumProgram` whose items cover all pubs (plus a TREX calibration
        item appended last when measurement mitigation is active).
    """
    resilience = finalized_options.resilience
    twirling = finalized_options.twirling

    task_class = choose_task_class(resilience)
    inject_noise = task_class in (PEC, PEA)

    # PEC uses its own shot-split logic, all other pathways use the standard twirling shot split.
    if task_class is PEC:
        num_randomizations, shots_per_randomization = calculate_pec_twirling_shots(
            shots,
            twirling.num_randomizations,
            twirling.shots_per_randomization,
        )
    elif twirling.enable_gates or twirling.enable_measure:
        num_randomizations, shots_per_randomization = calculate_twirling_shots(
            shots,
            twirling.num_randomizations,
            twirling.shots_per_randomization,
        )
    else:
        num_randomizations, shots_per_randomization = 1, shots

    # Setup
    boxing_options = estimator_options_to_boxing_options(
        twirling, bool(resilience.measure_mitigation), inject_noise, add_tags
    )
    noise_model = {}
    if resilience.layer_noise_model is not None:
        noise_model = {
            annotation.ref: pauli_map
            for instr, pauli_map in resilience.layer_noise_model
            for annotation in (get_annotation(instr.operation, InjectNoise),)
            if annotation is not None
        }
    measure_noise_learning = (
        resilience.measure_noise_learning if resilience.measure_mitigation else None
    )
    trex: TREX | None = TREX() if measure_noise_learning is not None else None

    # Build the quantum program
    quantum_program = QuantumProgram(shots=shots_per_randomization)

    for pub_index, pub in enumerate(coerced_pubs):
        logger.info(
            "Processing pub %d/%d with %s.", pub_index + 1, len(coerced_pubs), task_class.__name__
        )
        task = task_class()
        task.prepare(
            circuit=pub.circuit,
            observables=pub.observables,
            parameters=pub.parameter_values,
            custom_boxing_options=boxing_options,
            shots_per_randomization=shots_per_randomization,
            num_randomizations=num_randomizations,
            broadcast_obs_and_params=True,
            trex=trex,
            quantum_program=quantum_program,
            **build_task_prepare_kwargs(
                task_class, resilience, noise_model, num_randomizations, shots_per_randomization
            ),
        )

    # TREX finalisation (must be after all task.prepare() calls)
    if trex is not None:
        apply_trex(trex, quantum_program, measure_noise_learning, num_randomizations)

    # Dynamical decoupling
    if finalized_options.dynamical_decoupling.enable:
        logger.info("Applying dynamical decoupling.")
        quantum_program = apply_dynamical_decoupling(
            backend=backend,
            dd_options=finalized_options.dynamical_decoupling,
            quantum_program=quantum_program,
        )

    return quantum_program


def normalise_extrapolator(extrapolator: str | Sequence[str]) -> list[str]:
    """Return ``extrapolator`` as a plain list of strings."""
    return [extrapolator] if isinstance(extrapolator, str) else list(extrapolator)


def build_task_prepare_kwargs(
    task_class: type,
    resilience: ResilienceOptions,
    noise_model: dict,
    num_randomizations: int,
    shots_per_randomization: int,
) -> dict:
    """Return the pathway-specific keyword arguments for ``task.prepare()``.

    These are the arguments that differ between PEC, PEA, ZNE, and vanilla.
    Everything common (circuit, observables, parameters, boxing_opts, shots,
    trex, quantum_program) is passed by the caller.
    """
    if task_class is PEC:
        max_overhead = resolve_pec_max_overhead(
            resilience.pec.max_overhead, num_randomizations, shots_per_randomization
        )
        return {
            "noise_maps": noise_model,
            "noise_gain": resilience.pec.noise_gain,
            "max_sampling_overhead": max_overhead,
        }

    if task_class in (PEA, GateFolding):
        zne_options = resilience.zne
        noise_factors, extrapolated_noise_factors = resolve_noise_factors(zne_options)
        kwargs: dict = {
            "noise_factors": noise_factors.tolist(),
            "extrapolator": normalise_extrapolator(zne_options.extrapolator),
            "extrapolated_noise_factors": extrapolated_noise_factors.tolist(),
        }
        if task_class is PEA:
            kwargs["noise_maps"] = noise_model
        else:  # ZNE
            kwargs["folding_method"] = _ZNE_FOLDING_METHOD[zne_options.amplifier]
        return kwargs

    # MitigationTask (vanilla) — no extra kwargs
    return {}
