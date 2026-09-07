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

"""Shared TREX finalization helper for the executor-based EstimatorV2."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit_mitigation import TREX
    from samplomatic.quantum_program import QuantumProgram

    from ..options_models.measure_noise_learning import MeasureNoiseLearningOptions

logger = logging.getLogger(__name__)


def apply_trex(
    trex: TREX,
    quantum_program: QuantumProgram,
    measure_noise_learning: MeasureNoiseLearningOptions,
    num_randomizations: int,
) -> None:
    """Append the TREX calibration circuit to ``quantum_program``.

    Must be called **after** all per-pub ``task.prepare(trex=trex, ...)`` calls.
    By that point every task has registered itself on ``trex`` (via
    ``trex._edit_boxing_options``), so ``trex.tasks`` is fully populated.

    This calls ``trex.prepare()``, which:

    - Sizes the calibration circuit to the widest circuit across all registered tasks.
    - Appends it as the next item in ``quantum_program.items``.
    - Writes a ``"mitigation": "trex"`` entry into
      ``quantum_program.passthrough_data["qiskit_mitigation"]``.
    - Retroactively sets ``"trex_calibration": True`` on all previously written
      task entries in that list.

    Args:
        trex: The ``TREX`` instance that was passed to each ``task.prepare()`` call.
        quantum_program: The quantum program already containing all per-pub items.
        measure_noise_learning: Measure noise learning options used to resolve
            the number of TREX calibration randomizations.
        num_randomizations: The twirling ``num_randomizations`` used for the main
            circuit items, used when ``measure_noise_learning.num_randomizations``
            is ``"auto"``.
    """
    trex_num_randomizations = _resolve_trex_num_randomizations(
        measure_noise_learning, num_randomizations
    )
    trex.prepare(trex_num_randomizations, quantum_program)
    logger.info("TREX calibration circuit added (%d randomizations).", trex_num_randomizations)


def _resolve_trex_num_randomizations(
    measure_noise_learning: MeasureNoiseLearningOptions,
    twirling_num_randomizations: int,
) -> int:
    """Return the number of TREX randomizations, resolving ``"auto"`` if needed."""
    num_randomizations = measure_noise_learning.num_randomizations
    if num_randomizations == "auto":
        return twirling_num_randomizations
    return int(num_randomizations)
