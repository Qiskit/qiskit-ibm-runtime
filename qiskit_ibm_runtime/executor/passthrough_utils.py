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

"""Utility functions for passthrough data validation shared between sampler and estimator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from qiskit.primitives.containers.sampler_pub import SamplerPub


def validate_and_extract_metadata(
    pubs: Sequence[EstimatorPub] | Sequence[SamplerPub],
) -> list[dict[str, Any] | None]:
    """Validate and extract circuit metadata from a sequence of pubs.

    This function collects circuit metadata from each pub and validates that
    all metadata is compatible with the DataTree format.

    Args:
        pubs: Sequence of estimator or sampler pubs to extract metadata from.

    Returns:
        List of circuit metadata dictionaries (or None for pubs without metadata).

    Raises:
        IBMInputValueError: If any circuit metadata is not compatible with DataTree format.
    """
    circuits_metadata = [pub.circuit.metadata for pub in pubs]
    return circuits_metadata
