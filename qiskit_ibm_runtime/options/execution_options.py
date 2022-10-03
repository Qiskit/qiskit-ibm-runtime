# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Execution options."""

from typing import Optional, List
from dataclasses import dataclass

from .utils import _flexible


@_flexible
@dataclass
class ExecutionOptions:
    """Execution options.

    Args:
        shots: Number of repetitions of each circuit, for sampling. Default: 4000.

        qubit_lo_freq: List of job level qubit drive LO frequencies in Hz. Overridden by
            ``schedule_los`` if specified. Must have length ``n_qubits.``

        meas_lo_freq: List of measurement LO frequencies in Hz. Overridden by ``schedule_los`` if
            specified. Must have length ``n_qubits.``

        schedule_los: Experiment level (ie circuit or schedule) LO frequency configurations for
            qubit drive and measurement channels. These values override the job level values from
            ``default_qubit_los`` and ``default_meas_los``. Frequencies are in Hz. Settable for qasm
            and pulse jobs.

        rep_delay: Delay between programs in seconds. Only supported on certain
            backends (if ``backend.configuration().dynamic_reprate_enabled=True``).
            If supported, it must be from the range supplied by the backend
            (``backend.configuration().rep_delay_range``).
            Default is given by ``backend.configuration().default_rep_delay``.

        init_qubits: Whether to reset the qubits to the ground state for each shot.
            Default: ``True``.
    """

    shots: int = 4000
    qubit_lo_freq: Optional[List[float]] = None
    meas_lo_freq: Optional[List[float]] = None
    # TODO: need to be able to serialize schedule_los before we can support it
    rep_delay: Optional[float] = None
    init_qubits: bool = True
