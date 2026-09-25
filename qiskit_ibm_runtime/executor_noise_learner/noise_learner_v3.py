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

"""Noise learner program."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..base_primitive import get_mode_service_backend
from ..executor import Executor
from ..options_models.noise_learner_v3 import NoiseLearnerV3Options
from .prepare import prepare

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction
    from qiskit.providers import BackendV2

    from ..batch import Batch
    from ..fake_provider.local_runtime_job import LocalRuntimeJob
    from ..runtime_job_v2 import RuntimeJobV2
    from ..session import Session

logger = logging.getLogger(__name__)


class NoiseLearnerV3:
    """Class for executing noise learning experiments.

    The noise learner allows characterizing the noise processes affecting target instructions, based
    on the Pauli-Lindblad noise model described in [1]. The instructions provided to the
    :meth:`~run` method must contain a twirled-annotated :class:`~.qiskit.circuit.BoxOp` containing
    ISA operations. The result of a noise learner job contains a list of
    :class:`.NoiseLearnerV3Result` objects, one for each given instruction.

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`Backend` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.

            Refer to the
            `IBM Quantum Compute (formerly Qiskit Runtime) documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`__
            for more information about the execution modes.

        options: The desired options.

    References:
        1. E. van den Berg, Z. Minev, A. Kandala, K. Temme, *Probabilistic error
           cancellation with sparse Pauli–Lindblad models on noisy quantum processors*,
           Nature Physics volume 19, pages 1116–1121 (2023).
           `arXiv:2201.09866 [quant-ph] <https://arxiv.org/abs/2201.09866>`_
    """

    options: NoiseLearnerV3Options
    """The options in this noise learner."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: NoiseLearnerV3Options | dict | None = None,
    ):
        # Coerced to `NoiseLearnerV3Options` via `__setattr__()`.
        self.options = options if options is not None else NoiseLearnerV3Options()  # type: ignore[assignment]

        self._mode, self._service, self._backend = get_mode_service_backend(mode)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute ``name`` to ``value``.

        Handle ``options`` as a special case, ensuring it is set to a ``NoiseLearnerV3Options``
        instance. This is an alternative to using ``@setter``, as the setter causes issues in
        ``ipython`` autocomplete features.
        """
        if name == "options":
            if isinstance(value, dict):
                value = NoiseLearnerV3Options(**value)
            elif not isinstance(value, NoiseLearnerV3Options):
                raise TypeError(f"Expected NoiseLearnerV3Options or dict, got {type(value)}")
        super().__setattr__(name, value)

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

    def run(
        self, instructions: Iterable[CircuitInstruction], dry_run: bool = False
    ) -> RuntimeJobV2 | LocalRuntimeJob:
        """Submit a request to the noise learner program.

        Args:
            instructions: The instructions to learn the noise of.
            dry_run: If ``True``, performs a dry run without executing the job on a QPU. This mode
                can be used to validate the job, estimate usage consumption, and retrieve circuit
                timing metadata. Returned results preserve the expected schema but contain
                **randomized mock data** rather than actual or simulated measurement results.
                Unlike the fake backends, the processing of this dry run happens on the server-side,
                so the job may not finish immediately and access to this feature may be restricted.

        Returns:
            The submitted job.
        """
        logger.info("Starting pre-processing")
        quantum_program, executor_options = prepare(
            instructions=instructions,
            options=self.options,
            backend=self._backend,
        )

        # Set semantic role for post-processing dispatch
        quantum_program._semantic_role = "noise_learner_v3"

        executor = Executor(mode=self._mode or self._backend, options=executor_options)

        logger.info(
            "Submitting %d instructions%s to executor with %d total shots",
            len(quantum_program.items),
            "s" if len(quantum_program.items) > 1 else "",
            quantum_program.shots * sum(item.size() for item in quantum_program.items),
        )

        return executor.run(quantum_program, dry_run=dry_run)
