# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Unit tests for the visualization folder."""

from types import ModuleType

import pytest

from qiskit_ibm_runtime.visualization.utils import plotly_module


class TestUtils:
    """Tests for the utility module."""

    def test_get_plotly_module(self) -> None:
        """Test that getting a module works."""
        assert isinstance(plotly_module(), ModuleType)
        assert isinstance(plotly_module(".graph_objects"), ModuleType)

    def test_plotly_module_raises(self) -> None:
        """Test that correct error is raised."""
        with pytest.raises(
            ModuleNotFoundError,
            match="Install all qiskit-ibm-runtime visualization dependencies",
        ):
            plotly_module(".not_a_module")
