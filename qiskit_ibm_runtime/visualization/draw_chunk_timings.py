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

"""Function to visualize chunk timings from a :class:`~.QuantumProgramResult`."""

from samplomatic.visualization.draw_chunk_timings import draw_chunk_timings  # noqa: F401

from ..utils.deprecation import issue_deprecation_msg

issue_deprecation_msg(
    msg="Importing 'draw_chunk_timings' from 'qiskit_ibm_runtime.visualization.draw_chunk_timings' "
    "is deprecated",
    version="0.50.0",
    remedy="Import 'draw_chunk_timings' from 'samplomatic.visualization.draw_chunk_timings' "
    "instead.",
    stacklevel=2,
)
