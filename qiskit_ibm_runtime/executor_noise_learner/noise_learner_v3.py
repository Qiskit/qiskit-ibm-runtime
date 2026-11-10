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
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..base_client_side import BaseClientSide
from ..executor import Executor
from ..options_models.noise_learner_v3 import NoiseLearnerV3Options
from ..quantum_program import QuantumProgram
from .prepare import prepare

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction

    from ..fake_provider.local_runtime_job import LocalRuntimeJob
    from ..options_models import ExecutorOptions
    from ..runtime_job_v2 import RuntimeJobV2

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NoiseLearnerV3Inputs:
    """The inputs of NoiseLearnerV3."""

    instructions: Iterable[CircuitInstruction]


class NoiseLearnerV3(BaseClientSide[NoiseLearnerV3Inputs, NoiseLearnerV3Options]):
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

    semantic_role = "noise_learner_v3"

    def _get_default_options(self) -> NoiseLearnerV3Options:
        """The default options of all :class:`~.NoiseLearnerV3` objects."""
        return NoiseLearnerV3Options()

    def prepare(self, **kwargs: NoiseLearnerV3Inputs) -> tuple[QuantumProgram, ExecutorOptions]:
        """The function used to map the inputs of NoiseLearnerV3 to the inputs of Executor.

        Returns:
            A :class:`~.QuantumProgram` suitable for execution, along with the corresponding
                :class:`~.ExecutorOptions`.
        """
        return prepare(
            instructions=kwargs["instructions"],  # type: ignore[arg-type]
            options=self.options,
            backend=self._backend,
        )

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
