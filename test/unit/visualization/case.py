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

"""Helpers for visualization tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure

ARTIFACT_DIR = ".test_artifacts"


def save_plotly_artifact(test_id: str, fig: PlotlyFigure) -> str:
    """Save a Plotly figure as an HTML artifact, nested under `ARTIFACT_DIR` by `test_id`.

    Args:
        test_id: the dotted id of the test (`package.module.Class.method`).
        fig: the figure to save.

    Returns:
        The path of the saved artifact.
    """
    # nested folder path based on the test module, class, and method
    test_path = test_id.split(".")[1:]
    nested_dir = os.path.join(ARTIFACT_DIR, *test_path[:-1])
    name = test_path[-1]
    os.makedirs(nested_dir, exist_ok=True)

    # save figure
    artifact_path = os.path.join(nested_dir, f"{name}.html")
    fig.write_html(artifact_path)
    return artifact_path
