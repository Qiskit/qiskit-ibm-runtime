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
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .base_primitive import get_mode_service_backend

if TYPE_CHECKING:
    from qiskit.providers import BackendV2

    from .batch import Batch
    from .options_models import ExecutorOptions
    from .options_models.base import BaseOptionsModel
    from .quantum_program import QuantumProgram
    from .session import Session

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

    options: OptionsT
    """The options of this program."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: OptionsT | dict | None = None,
    ):
        super().__init__()

        self._mode, self._service, self._backend = get_mode_service_backend(mode)
        self.options = options if options is not None else self._get_default_options()  # type: ignore[assignment]

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute ``name`` to ``value``.

        Handle ``options`` as a special case, ensuring it is set to an ``OptionsT`` instance.
        This is an alternative to using ``@setter``, as the setter causes issues in ``ipython``
        autocomplete features.
        """
        if name == "options":
            if isinstance(value, dict):
                options = self._get_default_options()
                options.update(**value)
                value = options
            elif not isinstance(value, type(self._get_default_options())):
                name = self._get_default_options().__class__.__name__
                raise TypeError(f"Expected {name} or dict, got {type(value)}")

        super().__setattr__(name, value)

    @abstractmethod
    def _get_default_options(self) -> OptionsT:
        """The default options of this program."""

    @abstractmethod
    def prepare(self, **kwargs: InputT) -> tuple[QuantumProgram, ExecutorOptions]:
        """The function used to map this program's inputs to the inputs of Executor."""

    def backend(self) -> BackendV2:
        """Return the backend the primitive query will be run on."""
        return self._backend

    @property
    def mode(self) -> Session | Batch | None:
        """Return the execution mode used by this primitive.

        Returns:
            Mode used by this primitive, or ``None`` if an execution mode is not used.
        """
        return self._mode
