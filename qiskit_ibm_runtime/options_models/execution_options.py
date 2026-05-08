# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Execution options."""

from typing import Literal

from pydantic.dataclasses import dataclass

from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class ExecutionOptions:
    """Low-level execution options."""

    init_qubits: bool = True
    """Whether to reset the qubits to the ground state for each shot."""

    rep_delay: float | None = None
    """The repetition delay.

    This is the delay between a measurement and the subsequent quantum circuit. This is only
    supported on backends that have ``backend.dynamic_reprate_enabled=True``. It must be from the
    range supplied by ``backend.rep_delay_range``.

    Default is given by ``backend.default_rep_delay``.
    """

    scheduler_timing: bool = False
    """Whether to return circuit schedule timing of each provided quantum circuit.

    Setting this value to ``True`` will cause corresponding metadata of every program item to be
    populated in the returned data.

    Note: This feature is experimental and subject to change without notice.
    """

    stretch_values: bool = False
    """Whether to return numeric resolutions of stretches for each provided quantum circuit.

    Setting this value to ``True`` will cause corresponding metadata of every program item to be
    populated in the returned data.

    Note: This feature is experimental and subject to change without notice.
    """


@dataclass(config=PRIMITIVES_CONFIG)
class SamplerExecutionOptions(ExecutionOptions):
    """Execution options for the sampler primitive.

    Args:
        init_qubits: Whether to reset the qubits to the ground state for each shot.
            Inherited from :class:`~.ExecutionOptions`.
        rep_delay: The repetition delay. Inherited from :class:`~.ExecutionOptions`.
        meas_type: How to process and return measurement results. This option sets
            the return type of all classical registers in all sampler pub results.

            * ``"classified"``: Returns a BitArray with classified measurement outcomes.
            * ``"kerneled"``: Returns complex IQ data points from kerneling the measurement
              trace, in arbitrary units.
            * ``"avg_kerneled"``: Returns complex IQ data points averaged over shots,
              in arbitrary units.
    """

    meas_type: Literal["classified", "kerneled", "avg_kerneled"] = "classified"
