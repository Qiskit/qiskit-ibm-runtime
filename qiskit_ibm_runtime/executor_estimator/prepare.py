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
from qiskit_mitigation import PEA, PEC, TREX, ZNE, MitigationTask
from samplomatic.quantum_program import QuantumProgram

from ..exceptions import IBMInputValueError
from ..executor.calculate_twirling_shots import calculate_twirling_shots
from ..executor.dynamical_decoupling import apply_dynamical_decoupling
from ..options_models.converters import estimator_options_to_executor_options
from ..utils.utils import validate_no_boxes
from .finalize_options import finalize_estimator_options
from .options_to_mitigation import (
    estimator_options_to_boxing_options,
    layer_noise_model_to_dict,
    resolve_pec_max_overhead,
    resolve_zne_noise_factors,
)
from .trex_setup import apply_trex
from .utils import has_projection_operators, resolve_precision, validate_noise_factors

# Maps the user-facing ZNE amplifier name to qiskit-mitigation's folding_method string.
# _VALID_AMPLIFIERS in _validate() is derived from these keys plus "pea".
_ZNE_FOLDING_METHOD: dict[str, str] = {
    "gate_folding": "random",
    "gate_folding_front": "front",
    "gate_folding_back": "back",
}

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPubLike
    from qiskit.providers import BackendV2

    from ..options_models.estimator import EstimatorOptions
    from ..options_models.executor import ExecutorOptions
    from ..options_models.resilience import ResilienceOptions

logger = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(
    coerced_pubs: Sequence[EstimatorPub],
    finalized_options: EstimatorOptions,
    backend: BackendV2 | None,
) -> None:
    if not coerced_pubs:
        raise IBMInputValueError("No pubs provided. At least one pub is required.")
    if finalized_options.resilience.pec_mitigation and finalized_options.resilience.zne_mitigation:
        raise IBMInputValueError(
            "PEC mitigation and ZNE mitigation are incompatible with one another."
        )

    resilience = finalized_options.resilience
    if resilience.zne_mitigation:
        zne = resilience.zne
        # Gaps B+C: enforce valid amplifier values up front.
        _VALID_AMPLIFIERS = {"pea"} | set(_ZNE_FOLDING_METHOD)
        if zne.amplifier not in _VALID_AMPLIFIERS:
            raise IBMInputValueError(
                "ZNE mitigation must use a gate folding or 'pea' noise amplification method. "
                f"Got: '{zne.amplifier}'."
            )
        # Gap A: validate noise_factors has enough points for every requested extrapolator.
        noise_factors, _ = resolve_zne_noise_factors(zne)
        extrapolator = (
            list(zne.extrapolator) if not isinstance(zne.extrapolator, str) else [zne.extrapolator]
        )
        validate_noise_factors(noise_factors, extrapolator)

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


# ---------------------------------------------------------------------------
# Program building
# ---------------------------------------------------------------------------


def _build_quantum_program(
    coerced_pubs: Sequence[EstimatorPub],
    finalized_options: EstimatorOptions,
    shots: int,
    add_tags: bool,
    backend: BackendV2 | None,
) -> QuantumProgram:
    """Dispatch to the appropriate mitigation pathway and apply dynamical decoupling."""
    resilience = finalized_options.resilience
    twirling = finalized_options.twirling

    # ── Shot split ────────────────────────────────────────────────────────────
    # PEC uses its own shot-split logic (with a smaller default shots_per_rand).
    # All other pathways use the standard twirling shot split.
    if resilience.pec_mitigation:
        from .pec.utils import calculate_pec_twirling_shots

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

    # ── Boxing options (shared across all pubs) ───────────────────────────────
    inject_noise = resilience.pec_mitigation or (
        resilience.zne_mitigation and resilience.zne.amplifier == "pea"
    )
    boxing_opts = estimator_options_to_boxing_options(twirling, inject_noise, add_tags)

    # ── Noise model (PEC / PEA only) ──────────────────────────────────────────
    noise_model = layer_noise_model_to_dict(resilience.layer_noise_model or [])

    # ── Task class selection ──────────────────────────────────────────────────
    if resilience.pec_mitigation:
        task_class = PEC
    elif resilience.zne_mitigation and resilience.zne.amplifier == "pea":
        task_class = PEA
    elif resilience.zne_mitigation:
        task_class = ZNE
    else:
        task_class = MitigationTask

    # ── TREX instance (one shared across all pubs) ────────────────────────────
    measure_noise_learning = (
        resilience.measure_noise_learning if resilience.measure_mitigation else None
    )
    trex: TREX | None = TREX() if measure_noise_learning is not None else None

    # ── Quantum program (shots locked here) ───────────────────────────────────
    qp = QuantumProgram(shots=shots_per_randomization)

    # ── Per-pub loop ──────────────────────────────────────────────────────────
    for i, pub in enumerate(coerced_pubs):
        logger.info("Processing pub %d/%d with %s.", i + 1, len(coerced_pubs), task_class.__name__)
        task = task_class()
        task.prepare(
            circuit=pub.circuit,
            observables=pub.observables,
            parameters=pub.parameter_values,
            custom_boxing_options=dict(boxing_opts),  # fresh copy per pub
            shots_per_randomization=shots_per_randomization,
            num_randomizations=num_randomizations,
            broadcast_obs_and_params=True,
            trex=trex,
            quantum_program=qp,
            **_method_kwargs(
                task_class, resilience, noise_model, num_randomizations, shots_per_randomization
            ),
        )

    # ── TREX finalisation (must be after all task.prepare() calls) ────────────
    if trex is not None:
        apply_trex(trex, qp, measure_noise_learning, num_randomizations)

    # ── Dynamical decoupling ──────────────────────────────────────────────────
    if finalized_options.dynamical_decoupling.enable:
        logger.info("Applying dynamical decoupling.")
        qp = apply_dynamical_decoupling(
            backend=backend,
            dd_options=finalized_options.dynamical_decoupling,
            quantum_program=qp,
        )

    return qp


def _method_kwargs(
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

    if task_class is PEA:
        zne = resilience.zne
        noise_factors, extrapolated_noise_factors = resolve_zne_noise_factors(zne)
        extrapolator = (
            list(zne.extrapolator) if not isinstance(zne.extrapolator, str) else [zne.extrapolator]
        )
        return {
            "noise_maps": noise_model,
            "noise_factors": noise_factors.tolist(),
            "extrapolator": extrapolator,
            "extrapolated_noise_factors": extrapolated_noise_factors.tolist(),
        }

    if task_class is ZNE:
        zne = resilience.zne
        noise_factors, extrapolated_noise_factors = resolve_zne_noise_factors(zne)
        extrapolator = (
            list(zne.extrapolator) if not isinstance(zne.extrapolator, str) else [zne.extrapolator]
        )
        return {
            "folding_method": _ZNE_FOLDING_METHOD[zne.amplifier],
            "noise_factors": noise_factors.tolist(),
            "extrapolator": extrapolator,
            "extrapolated_noise_factors": extrapolated_noise_factors.tolist(),
        }

    # MitigationTask (vanilla) — no extra kwargs
    return {}
