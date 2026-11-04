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

"""Hooks shared by all the tests."""

from __future__ import annotations

import pytest

# Deprecation messages expected for the server-side primitives.
SERVER_SIDE_DEPRECATIONS = (
    "The EstimatorV2 class is deprecated",
    "The SamplerV2 class is deprecated",
    "The NoiseLearner class is deprecated",
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Silence the server-side deprecations in the marked `server_side_primitives` tests."""
    for item in items:
        if item.get_closest_marker("server_side_primitives") is None:
            continue
        for message in SERVER_SIDE_DEPRECATIONS:
            item.add_marker(pytest.mark.filterwarnings(f"ignore:{message}:DeprecationWarning"))
