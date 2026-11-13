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
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from .base_primitive import get_mode_service_backend
from .executor import Executor
from .quantum_program import QuantumProgram

if TYPE_CHECKING:
    from qiskit.providers import BackendV2

    from .batch import Batch
    from .fake_provider.local_runtime_job import LocalRuntimeJob
    from .options_models import ExecutorOptions
    from .options_models.base import BaseOptionsModel
    from .runtime_job_v2 import RuntimeJobV2
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

    semantic_role: Literal["sampler_v2", "noise_learner_v3", "estimator_v2"]

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
    def prepare(self, inputs: InputT) -> tuple[QuantumProgram, ExecutorOptions]:
        """The function used to map this program's inputs to the inputs of Executor.

        Args:
            inputs: The inputs of this program.

        Returns:
            A :class:`~.QuantumProgram` suitable for execution, along with the corresponding
                :class:`~.ExecutorOptions`.
        """

    def _run(self, inputs: InputT, dry_run: bool = False) -> RuntimeJobV2 | LocalRuntimeJob:
        """Prepare this program's inputs and submit the resulting quantum program to the executor.

        Args:
            inputs: The inputs of this program, forwarded to :meth:`prepare`.
            dry_run: If ``True``, performs a dry run without executing the job on a QPU. This
                mode can be used to validate the job, estimate usage consumption, and retrieve
                circuit timing metadata. Returned results preserve the expected schema but
                contain **randomized mock data** rather than actual or simulated measurement
                results. Unlike the fake backends, the processing of this dry run happens on the
                server-side, so the job may not finish immediately and access to this feature
                may be restricted.

        Returns:
            The submitted job.
        """
        logger.info("Starting pre-processing")
        quantum_program, executor_options = self.prepare(inputs)

        # Some `prepare` implementations return a `samplomatic.QuantumProgram` rather than the
        # `QuantumProgram` subclass, so normalize before tagging the semantic role.
        quantum_program = QuantumProgram.from_(quantum_program)
        quantum_program._semantic_role = self.semantic_role

        executor = Executor(mode=self._mode or self._backend, options=executor_options)

        logger.info(
            "Submitting %d item%s to executor with %d total shots",
            len(quantum_program.items),
            "s" if len(quantum_program.items) > 1 else "",
            quantum_program.shots * sum(item.size() for item in quantum_program.items),
        )

        return executor.run(quantum_program, dry_run=dry_run)

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
