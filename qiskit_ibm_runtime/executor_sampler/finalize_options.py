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

"""Utility for finalizing SamplerOptions."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..options_models.sampler import SamplerOptions


def finalize_sampler_options(options: SamplerOptions) -> SamplerOptions:
    """Return a finalized copy of *options*.

    Resolves the ``None`` sentinel values in the twirling options to their effective
    defaults (``False`` for both ``enable_gates`` and ``enable_measure``).

    Args:
        options: The un-finalized :class:`~.SamplerOptions` to process.

    Returns:
        A finalized copy of the given :class:`~.SamplerOptions`.
    """
    finalized_options = deepcopy(options)

    if finalized_options.twirling.enable_gates is None:
        finalized_options.twirling.enable_gates = False
    if finalized_options.twirling.enable_measure is None:
        finalized_options.twirling.enable_measure = False

    return finalized_options
