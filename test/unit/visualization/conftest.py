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

"""Fixtures shared by the visualization tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def test_id(request: pytest.FixtureRequest) -> str:
    """Return the dotted id of the test, as `package.module.Class.method`.

    This replaces `unittest`'s `TestCase.id()`, which the artifact helpers expect: they split
    the id on dots to build a nested directory for the saved figure.
    """
    return f"{request.node.module.__name__}.{request.node.cls.__name__}.{request.node.name}"
