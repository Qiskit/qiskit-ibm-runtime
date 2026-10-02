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

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure

ARTIFACT_DIR = Path(".test_artifacts")


def save_plotly_artifact(test_id: str, fig: PlotlyFigure) -> Path:
    """Save a Plotly figure as an HTML artifact, nested under `ARTIFACT_DIR` by `test_id`.

    Args:
        test_id: the dotted id of the test (`package.module.Class.method`).
        fig: the figure to save.

    Returns:
        The path of the saved artifact.
    """
    # Nested folder path based on the test module, class, and method.
    *test_path, name = test_id.split(".")[1:]
    nested_dir = ARTIFACT_DIR.joinpath(*test_path)
    nested_dir.mkdir(parents=True, exist_ok=True)

    # Save figure.
    artifact_path = nested_dir / f"{name}.html"
    fig.write_html(artifact_path)
    return artifact_path
