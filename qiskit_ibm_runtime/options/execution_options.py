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

from pydantic.dataclasses import dataclass

from .utils import Unset, UnsetType, primitive_dataclass, PRIMITIVES_CONFIG


@primitive_dataclass
class ExecutionOptionsV2:
    """Execution options for V2 primitives."""

    init_qubits: UnsetType | bool = Unset
    """Whether to reset the qubits to the ground state for each shot. Default is ``True``."""

    rep_delay: UnsetType | float = Unset
    """The repetition delay.

    This is the delay between a measurement and the subsequent quantum circuit. This is only
    supported on backends that have ``backend.dynamic_reprate_enabled=True``. It must be from the
    range supplied by ``backend.rep_delay_range``.

    Default is given by ``backend.default_rep_delay``.
    """


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
