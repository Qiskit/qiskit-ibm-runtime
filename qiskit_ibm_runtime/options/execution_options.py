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

from typing import Union

from .utils import Unset, UnsetType, primitive_dataclass


@primitive_dataclass
class ExecutionOptionsV2:
    """Execution options for V2 primitives."""

    init_qubits: Union[UnsetType, bool] = Unset
    r"""Whether to reset the qubits to the ground state for each shot. Default is ``True``.
    """

    rep_delay: Union[UnsetType, float] = Unset
    r"""The repetition delay. This is the delay between a measurement and
    the subsequent quantum circuit. This is only supported on backends that have
    ``backend.dynamic_reprate_enabled=True``. It must be from the
    range supplied by ``backend.rep_delay_range``.
    Default is given by ``backend.default_rep_delay``.
    """
