# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""This module defines the functionality to visualize the schedule of a Qiskit circuit compiled code"""

from __future__ import annotations

from typing import TYPE_CHECKING
from ..utils.circuit_schedule import CircuitSchedule
from .utils import plotly_module

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


def draw_circuit_schedule_timing(
    circuit_schedule: str | CircuitSchedule,
    included_channels: list = None,
    filter_readout_channels: bool = False,
    filter_barriers: bool = False,
    width: int = 1400,
) -> PlotlyFigure:
    r"""
    Draw a circuit schedule timing for :class:`~.CircuitSchedule`.

    Args:
        circuit_schedule: The circuit schedule as a string as returned
        from the compiler or a `CircuitSchedule` object.
        included_channels: A list of channels to include in the plot.
        filter_readout_channels: If ``True``, remove all readout channels.
        filter_barriers: If ``True``, remove all barriers.
        width: The width of the returned figure.

    Returns:
        A plotly figure.
    """
    go = plotly_module(".graph_objects")
    fig = go.Figure(layout=go.Layout(width=width))

    # Get the scheduling data
    if isinstance(circuit_schedule, CircuitSchedule):
        schedule = circuit_schedule
    elif isinstance(circuit_schedule, str):
        schedule = CircuitSchedule(
            circuit_schedule=circuit_schedule,
        )
    else:
        raise ValueError(
            f"'circuit_schedule' is expected to be of type "
            f"'str' or 'CircuitSchedule', instead got {type(circuit_schedule)}."
        )

    # Process and filter
    schedule.preprocess(
        included_channels=included_channels,
        filter_awgr=filter_readout_channels,
        filter_barriers=filter_barriers,
    )

    # Setup the figure
    fig.update_layout(
        title_text="Payload Schedule",
        paper_bgcolor="rgba(255,255,255,1)",
        plot_bgcolor="rgba(255,255,255,1)",
        title_font_size=20,
        title_x=0.5,
    )
    fig.update_xaxes(
        range=(0, schedule.max_time + 1),  # TODO: Add X% padding if requested
        showline=True,
        linewidth=1,
        linecolor="black",
        mirror=True,
    )
    fig.update_yaxes(
        showline=True,
        linewidth=1,
        linecolor="black",
        mirror=True,
        gridcolor="rgba(38,38,38,0.15)",
    )
    fig.update_layout(
        xaxis_type="linear",
        xaxis_title="Cycles",  # TODO: convert to time if requested
        yaxis_title="Channels",
        height=200 + 60 * len(schedule.channels),
    )
    fig.update_layout(
        xaxis={
            "rangeselector": {"buttons": list([])},
            "rangeslider": {"visible": True},
        }
    )

    # Populate the figure with traces
    fig = schedule.populate_figure(fig=fig)

    # Add annotations
    fig["layout"]["annotations"] = schedule.annotations

    # Add a button to control annotations display
    fig.update_layout(
        updatemenus=[
            {
                "type": "dropdown",
                "direction": "down",
                "buttons": list(
                    [
                        {
                            "args": [{"annotations": fig.layout.annotations}],
                            "label": "Show Annotations",
                            "method": "relayout",
                        },
                        {
                            "args": [{"annotations": []}],
                            "label": "Hide Annotations",
                            "method": "relayout",
                        },
                    ]
                ),
                "pad": {"r": 10, "t": 10},
                "showactive": True,
                "x": 0,
                "xanchor": "left",
                "y": 1 + 1 / len(schedule.channels),
                "yanchor": "top",
            }
        ]
    )

    # Update the xtick values
    fig.update_layout(
        yaxis={
            "tickmode": "array",
            "tickvals": list(range(0, len(schedule.channels))),
            "ticktext": schedule.channels,
        }
    )

    # update annotation hovering
    fig.update_traces(
        hoverinfo="x+text",
        marker={"size": 0.01},
        mode="lines+markers",
    )

    return fig
