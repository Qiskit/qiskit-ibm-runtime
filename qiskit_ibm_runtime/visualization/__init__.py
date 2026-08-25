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

"""
==========================================================
Visualization (:mod:`qiskit_ibm_runtime.visualization`)
==========================================================

.. currentmodule:: qiskit_ibm_runtime.visualization

A suite of functions for visualizing qiskit-ibm-runtime's objects.

Functions
=========

.. autosummary::
    :toctree: ../stubs/
    :nosignatures:

    draw_execution_spans
    draw_layer_error_map
    draw_layer_errors_swarm
    draw_zne_evs
    draw_zne_extrapolators
    draw_circuit_schedule_timing
"""

from ..utils.deprecation import issue_deprecation_msg
from .draw_circuit_schedule_timings import draw_circuit_schedule_timing
from .draw_execution_spans import draw_execution_spans
from .draw_layer_error import draw_layer_error_map, draw_layer_errors_swarm
from .draw_zne import draw_zne_evs, draw_zne_extrapolators

_DEPRECATED_NAMES = frozenset({"draw_chunk_timings"})


def __getattr__(name: str) -> object:
    if name in _DEPRECATED_NAMES:
        import samplomatic.quantum_program as _sq

        issue_deprecation_msg(
            msg="Importing 'draw_chunk_timings' from 'qiskit_ibm_runtime.visualization' is "
            "deprecated",
            version="0.50.0",
            remedy="Import 'draw_chunk_timings' from "
            "'samplomatic.visualization.draw_chunk_timings' "
            "instead.",
            stacklevel=2,
        )
        return getattr(_sq, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
