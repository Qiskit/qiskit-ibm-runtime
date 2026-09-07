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

"""Post-processing for the executor-based EstimatorV2: delegates to qiskit-mitigation."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.primitives.containers import PrimitiveResult

    from ...results.quantum_program import QuantumProgramResult

import numpy as np
from qiskit.primitives import PrimitiveResult as _PrimitiveResult
from qiskit.primitives.containers.data_bin import DataBin
from qiskit_mitigation import PEA, PEC, ZNE, MitigationTask
from qiskit_mitigation.utils.utils import load_tasks_from_result

from ...results.estimator_pub import EstimatorPubResult
from ...results.quantum_program import ItemMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point (name kept for compatibility with the decoder registry)
# ---------------------------------------------------------------------------


def estimator_v2_post_processor_v0_1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert a quantum program result to a primitives result for EstimatorV2.

    Reads ``passthrough_data["qiskit_mitigation"]`` to reconstruct the per-pub
    mitigation task objects via ``load_tasks_from_result()``, then calls
    ``task.postprocess(result)`` for each pub.  TREX noise-model computation is
    handled automatically inside ``task.postprocess()`` when TREX is present.

    Runtime metadata (options, shots, precision, circuit metadata) is read from
    the separate ``passthrough_data["post_processor"]`` block, which is entirely
    owned by us and never written to by qiskit-mitigation.

    Args:
        result: The raw quantum program result containing measurement data.

    Returns:
        A :class:`~qiskit.primitives.PrimitiveResult` whose pub results are
        :class:`~qiskit_ibm_runtime.results.EstimatorPubResult` instances.
    """
    if len(result) == 0:
        return _PrimitiveResult([])

    if not isinstance(result.passthrough_data, dict):
        raise ValueError(
            "Wrong type for passthrough data: Expected a 'dict', found "
            f"'{type(result.passthrough_data)}'."
        )

    passthrough: dict[str, Any] = result.passthrough_data
    if (post_processor_data := passthrough.get("post_processor")) is None:
        raise ValueError("Missing 'post_processor' in passthrough data.")

    num_pubs: int = post_processor_data["num_pubs"]
    circuits_metadata: list[Any] = post_processor_data.get("circuits_metadata") or []

    # Reconstruct all task objects from the qiskit-mitigation passthrough block.
    # load_tasks_from_result returns exactly num_pubs entries (one per pub); the
    # TREX entry is consumed internally to wire up trex references on each task.
    tasks = load_tasks_from_result(result)

    if len(tasks) != num_pubs:
        raise ValueError(
            f"Expected {num_pubs} task(s) from passthrough data, "
            f"but load_tasks_from_result returned {len(tasks)}."
        )

    pub_results = []
    for i, task in enumerate(tasks):
        logger.info("Post-processing pub %d/%d (%s).", i + 1, num_pubs, type(task).__name__)

        # Workaround for upstream ZNE/PEA bug: both ZNE.prepare() and PEA.prepare()
        # store extrapolated_noise_factors as a numpy array; postprocess() then does
        # ``== []`` which raises "truth value of array is ambiguous".  Convert
        # back to a plain list so the comparison is well-defined.
        if isinstance(task, (ZNE, PEA)) and isinstance(
            getattr(task, "extrapolated_noise_factors", None), np.ndarray
        ):
            task.extrapolated_noise_factors = task.extrapolated_noise_factors.tolist()

        # Delegates all expectation-value math (PEC/PEA/ZNE/vanilla + TREX) to
        # qiskit-mitigation. task.postprocess() uses task._program_item_index to
        # slice the correct item(s) from result, and calls
        # trex.compute_noise_model(result) automatically when TREX is attached.
        pub_result_raw = task.postprocess(result)

        # Rename DataBin fields to our public API names.
        # qiskit-mitigation broadcast path (MitigationTask / PEC) produces:
        #   evs, stds (= ensemble stderr), twirl_stds (= twirl-level stderr)
        # Our API exposes:
        #   evs, ensemble_standard_error, stds
        pub_result_raw = _rename_databin_fields(pub_result_raw, task)

        # Build per-item compilation metadata.
        pub_meta: dict[str, Any]
        if isinstance(task, ZNE) and task.noise_factors is not None:
            # ZNE has one result item per noise factor; aggregate their metadata.
            num_nf = len(task.noise_factors)
            items_meta = [
                _create_pub_result_metadata(result[task._program_item_index + j].metadata)
                for j in range(num_nf)
            ]
            pub_meta = {key: [m[key] for m in items_meta] for key in items_meta[0]}
        else:
            pub_meta = _create_pub_result_metadata(result[task._program_item_index].metadata)

        if i < len(circuits_metadata) and (cm := circuits_metadata[i]) is not None:
            pub_meta["circuit_metadata"] = cm

        pub_results.append(EstimatorPubResult(data=pub_result_raw.data, metadata=pub_meta))

    metadata = _build_program_result_metadata(post_processor_data)
    metadata["executor"] = result.metadata
    return _PrimitiveResult(pub_results, metadata=metadata)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def expanded_values_to_lists(key_value_pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """Dict factory that converts ``expanded_values`` tuples to lists.

    Used as the ``dict_factory`` argument when calling ``dataclasses.asdict``
    on stretch-value objects that contain ``expanded_values`` fields.
    """
    d = dict(key_value_pairs)
    d["expanded_values"] = [list(i) for i in d["expanded_values"]]
    return d


def _create_pub_result_metadata(item_metadata: ItemMetadata | dict) -> dict[str, Any]:
    """Build the compilation metadata dict for a single result item."""
    result_item_metadata: dict[str, Any] = {}
    if isinstance(item_metadata, ItemMetadata):
        result_item_metadata["compilation"] = {}
        if item_metadata.scheduler_timing:
            result_item_metadata["compilation"]["scheduler_timing"] = {
                "timing": item_metadata.scheduler_timing.timing,
                "circuit_duration": item_metadata.scheduler_timing.circuit_duration,
            }
        if item_metadata.stretch_values:
            result_item_metadata["compilation"]["stretch_values"] = [
                asdict(sv, dict_factory=expanded_values_to_lists)
                for sv in item_metadata.stretch_values
            ]
    else:  # simulator result — metadata is a plain dict
        result_item_metadata["executor"] = item_metadata
    return result_item_metadata


def _rename_databin_fields(pub_result: Any, task: Any) -> Any:
    """Rename qiskit-mitigation DataBin fields to our public API field names.

    qiskit-mitigation's broadcast path for ``MitigationTask`` and ``PEC``
    produces a ``DataBin`` with::

        evs            – expectation values
        stds           – ensemble standard error (over all shots as one pool)
        twirl_stds     – twirl-level standard error (std of per-twirl estimates)

    Our public API names are::

        evs                    – same
        ensemble_standard_error – what qiskit-mitigation calls ``stds``
        stds                   – what qiskit-mitigation calls ``twirl_stds``

    When twirling is **not** enabled (1 randomization), ``stds`` and
    ``ensemble_standard_error`` are identical.

    ``ZNE`` and ``PEA`` produce different fields (extrapolation results) that
    already use the names our API expects, so they are returned unchanged.

    Args:
        pub_result: The raw :class:`~qiskit.primitives.PubResult` returned by
            ``task.postprocess()``.
        task: The qiskit-mitigation task object.

    Returns:
        The ``pub_result`` with a re-keyed ``DataBin`` when renaming is needed,
        or the original ``pub_result`` unchanged for ZNE/PEA.
    """
    from qiskit.primitives import PubResult

    db = pub_result.data

    # Only MitigationTask (vanilla) and PEC use the stds/twirl_stds naming.
    # ZNE and PEA already have the right names.
    if not isinstance(task, (MitigationTask, PEC)):
        return pub_result

    # Pull out current fields; twirl_stds may be absent on very old builds.
    evs = db.evs
    ensemble_standard_error = db.stds  # rename: stds → ensemble_standard_error
    twirl_stds = getattr(db, "twirl_stds", None)
    stds = (
        twirl_stds if twirl_stds is not None else ensemble_standard_error
    )  # rename: twirl_stds → stds

    renamed = DataBin(
        evs=evs,
        stds=stds,
        ensemble_standard_error=ensemble_standard_error,
        shape=evs.shape,
    )
    return PubResult(data=renamed, metadata=pub_result.metadata)


def _build_program_result_metadata(post_processor_data: dict) -> dict[str, Any]:
    """Reconstruct program-level metadata from the ``post_processor`` passthrough block."""
    options = post_processor_data.get("options")
    if options is None:
        return {}

    metadata: dict[str, Any] = {"options": dict(options)}
    if "resilience" in metadata["options"]:
        resilience = dict(metadata["options"]["resilience"])
        for flag_key, options_key in [
            ("zne_mitigation", "zne"),
            ("pec_mitigation", "pec"),
            ("measure_mitigation", "measure_noise_learning"),
        ]:
            if not resilience.get(flag_key):
                resilience.pop(options_key, None)
        metadata["options"]["resilience"] = resilience

    metadata["target_precision"] = post_processor_data.get("precision")
    metadata["shots"] = post_processor_data.get("shots")
    return metadata
