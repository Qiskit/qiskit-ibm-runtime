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

"""Fixtures shared by the integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .case import integration_test_dependencies

if TYPE_CHECKING:
    from .case import IntegrationTestDependencies


@pytest.fixture(scope="class")
def dependencies() -> IntegrationTestDependencies:
    """Return the dependencies of an integration test, from the environment configuration."""
    return integration_test_dependencies()
