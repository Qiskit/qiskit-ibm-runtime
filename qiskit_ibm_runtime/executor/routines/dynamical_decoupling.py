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

"""Dynamical decoupling utilities for executor routines."""

from __future__ import annotations
from typing import Literal

import numpy as np
from qiskit.circuit import Gate
from qiskit.circuit.library import RZGate, XGate
from qiskit.providers import BackendV2
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import (
    ALAPScheduleAnalysis,
    ASAPScheduleAnalysis,
    PadDelay,
    PadDynamicalDecoupling,
    TimeUnitConversion,
)

from .options.dynamical_decoupling_options import DynamicalDecouplingOptions


def make_dd_sequence(
    sequence_type: Literal["XX", "XpXm", "XY4"],
) -> tuple[list[Gate], list[float]]:
    """Generate DD gate sequence and spacing from sequence type.

    Converts DD sequence type into gate sequences and spacing for
    :class:`~qiskit.transpiler.passes.PadDynamicalDecoupling`.

    Args:
        sequence_type: Type of DD sequence ("XX", "XpXm", or "XY4").

    Returns:
        Tuple of (dd_sequence, spacing) where:
        - dd_sequence: List of gates to apply in idle spots
        - spacing: List of spacings between the DD gates (sums to 1.0)

    Raises:
        ValueError: If an invalid sequence_type is provided.
    """
    # Base gate sequences
    _xp = [XGate()]
    _xm = [RZGate(np.pi), XGate(), RZGate(-np.pi)]
    _yp = [RZGate(np.pi / 2), XGate(), RZGate(-np.pi / 2)]
    _ym = [RZGate(-np.pi / 2), XGate(), RZGate(np.pi / 2)]

    if sequence_type == "XX":
        dd_sequence_list = [_xp, _xp]
    elif sequence_type == "XpXm":
        dd_sequence_list = [_xp, _xm]
    elif sequence_type == "XY4":
        dd_sequence_list = [_xp, _yp, _xm, _ym]
    else:
        # This should be caught by various validations, but include for safety
        raise ValueError(f"Unknown sequence_type={sequence_type}. ")

    # Calculate spacing for the DD sequence
    delay = 1 / len(dd_sequence_list)
    dd_sequence = []
    spacing = []

    for i, sequence in enumerate(dd_sequence_list):
        # First and last intervals are half-sized, middle intervals are full-sized
        spacing.append(delay / 2 if i == 0 else delay)
        # Mutligate sequences happen with no delay
        spacing.extend([0] * (len(sequence) - 1))
        dd_sequence.extend(sequence)
    spacing.append(delay / 2)

    return dd_sequence, spacing


def generate_dd_pass_manager(
    backend: BackendV2,
    options: DynamicalDecouplingOptions,
) -> PassManager:
    """Create a pass manager that applies dynamical decoupling.

    This function creates a Qiskit :class:`~qiskit.transpiler.PassManager` that
    schedules circuits and applies dynamical decoupling sequences in idle periods
    based on the provided options.

    Args:
        backend: Backend to extract timing information from (target, instruction durations,
            pulse alignment).
        options: DD options containing sequence type and other parameters.

    Returns:
        :class:`~qiskit.transpiler.PassManager` configured for dynamical decoupling.

    Raises:
        ValueError: If backend doesn't have a target or if invalid options are provided.
    """
    # Generate dd_sequence and spacing from options
    dd_sequence, spacing = make_dd_sequence(options.sequence_type)

    target = backend.target
    if target is None:
        raise ValueError(
            "Backend must have a target to apply dynamical decoupling. "
            "The target provides timing information required for DD."
        )

    if options.scheduling_method == "alap":
        scheduling_pass = ALAPScheduleAnalysis(target=target)
    else:
        scheduling_pass = ASAPScheduleAnalysis(target=target)

    # Create the PadDynamicalDecoupling pass
    dd_pass = PadDynamicalDecoupling(
        skip_reset_qubits=options.skip_reset_qubits,
        dd_sequence=dd_sequence,
        spacing=spacing,
        extra_slack_distribution=options.extra_slack_distribution,
        target=target,
    )

    # Build the pass manager
    pm = PassManager()

    # Add time unit conversion if needed
    if target.dt is not None:
        pm.append(TimeUnitConversion(target=target))

    # Add scheduling analysis
    pm.append(scheduling_pass)

    # Add DD pass
    pm.append(dd_pass)

    # Add padding for any remaining delays
    pm.append(PadDelay(target=target))

    return pm
