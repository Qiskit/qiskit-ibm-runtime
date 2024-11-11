# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
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

from qiskit_ibm_runtime.visualization.utils import plotly_module

from ...ibm_test_case import IBMTestCase


class TestUtils(IBMTestCase):
    """Tests for the utility module."""

    def test_get_plotly_module(self):
        """Test that getting a module works."""
        self.assertIsInstance(plotly_module(), ModuleType)
        self.assertIsInstance(plotly_module(".graph_objects"), ModuleType)

    def test_plotly_module_raises(self):
        """Test that correct error is raised."""
        with self.assertRaisesRegex(
            ModuleNotFoundError, "Install all qiskit-ibm-runtime visualization dependencies"
        ):
            plotly_module(".not_a_module")
