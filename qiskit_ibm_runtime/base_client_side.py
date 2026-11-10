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

"""Base class for IBM Quantum Compute client-side primitives."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from .options_models import ExecutorOptions
    from .options_models.base import BaseOptionsModel
    from .quantum_program import QuantumProgram

InputT = TypeVar("InputT")
OptionsT = TypeVar("OptionsT", bound="BaseOptionsModel")

logger = logging.getLogger(__name__)


class BaseClientSide(ABC, Generic[InputT, OptionsT]):
    """Base class for all client-side execution models.

    Args:
        mode: The execution mode used to make the primitive query. It can be:
            * A :class:`~qiskit.providers.BackendV2` if you are using job mode.
            * A :class:`~qiskit_ibm_runtime.Session` if you are using session execution mode.
            * A :class:`~qiskit_ibm_runtime.Batch` if you are using batch execution mode.
            Refer to the `IBM Quantum Compute documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`__
            for more information about execution modes.
        options: The options of this program.
    """

    @abstractmethod
    def prepare(self, **kwargs: InputT) -> tuple[QuantumProgram, ExecutorOptions]:
        """The function used to map this program's inputs to the inputs of Executor."""
