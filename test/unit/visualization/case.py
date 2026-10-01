# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Custom TestCase for visualization tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ...ibm_test_case import IBMTestCase

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


def save_plotly_artifact(test_id: str, fig: PlotlyFigure, artifact_dir: str) -> str:
    """Save a Plotly figure as an HTML artifact, nested under `artifact_dir` by `test_id`.

    Args:
        test_id: the dotted id of the test (`package.module.Class.method`).
        fig: the figure to save.
        artifact_dir: the root directory for the artifacts.

    Returns:
        The path of the saved artifact.
    """
    # nested folder path based on the test module, class, and method
    test_path = test_id.split(".")[1:]
    nested_dir = os.path.join(artifact_dir, *test_path[:-1])
    name = test_path[-1]
    os.makedirs(nested_dir, exist_ok=True)

    # save figure
    artifact_path = os.path.join(nested_dir, f"{name}.html")
    fig.write_html(artifact_path)
    return artifact_path


class IBMVisualizationTestCase(IBMTestCase):
    """Test case for use with visualization-related features."""

    ARTIFACT_DIR = ".test_artifacts"

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        super().setUpClass()

        # Ensure the artifact directory exists
        os.makedirs(cls.ARTIFACT_DIR, exist_ok=True)

    def save_plotly_artifact(self, fig: PlotlyFigure, name: str | None = None) -> str:
        """Save a Plotly figure as an HTML artifact."""
        return save_plotly_artifact(self.id(), fig, self.ARTIFACT_DIR)
