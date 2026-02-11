# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
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
from collections.abc import Iterable

from qiskit.circuit import CircuitInstruction
from qiskit.providers import BackendV2

from qiskit_ibm_runtime.options.utils import UnsetType

from ..base_primitive import get_mode_service_backend
from ..batch import Batch
from ..fake_provider.local_service import QiskitRuntimeLocalService
from ..options.noise_learner_v3_options import NoiseLearnerV3Options
from ..runtime_job_v2 import RuntimeJobV2

# pylint: disable=unused-import,cyclic-import
from ..session import Session
from ..utils.default_session import get_cm_session
from .converters.version_0_1 import noise_learner_v3_inputs_to_0_1
from .noise_learner_v3_decoders import NoiseLearnerV3ResultDecoder
from .validation import validate_instruction, validate_options

logger = logging.getLogger(__name__)


class NoiseLearnerV3:
    """Class for executing noise learning experiments.

    The noise learner allows characterizing the noise processes affecting target instructions, based on
    the Pauli-Lindblad noise model described in [1]. The instructions provided to the :meth:`~run`
    method must contain a twirled-annotated :class:`~.qiskit.circuit.BoxOp` containing ISA operations.
    The result of a noise learner job contains a list of :class:`.NoiseLearnerV3Result` objects, one for
    each given instruction.

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`Backend` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.

            Refer to the
            `Qiskit Runtime documentation <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`__
            for more information about the execution modes.

        options: The desired options.

    References:
        1. E. van den Berg, Z. Minev, A. Kandala, K. Temme, *Probabilistic error
           cancellation with sparse Pauli–Lindblad models on noisy quantum processors*,
           Nature Physics volume 19, pages 1116–1121 (2023).
           `arXiv:2201.09866 [quant-ph] <https://arxiv.org/abs/2201.09866>`_
    """

    _PROGRAM_ID = "noise-learner"
    _DECODER = NoiseLearnerV3ResultDecoder

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: NoiseLearnerV3Options | None = None,
    ):
        self._options = options or NoiseLearnerV3Options()
        if (
            isinstance(self._options.experimental, UnsetType)
            or self._options.experimental.get("image") is None
        ):
            self._options.experimental = {}

        self._session, self._service, self._backend = get_mode_service_backend(
            mode
        )  # type: ignore[assignment]

        if isinstance(self._service, QiskitRuntimeLocalService):  # type: ignore[unreachable]
            raise ValueError("``NoiseLearnerV3`` is currently not supported in local mode.")

    @property
    def options(self) -> NoiseLearnerV3Options:
        """The options in this noise learner."""
        return self._options

    def run(self, instructions: Iterable[CircuitInstruction]) -> RuntimeJobV2:
        """Submit a request to the noise learner program.

            Args:
                instructions: The instructions to learn the noise of.

            Returns:
                The submitted job.

        Raises:
            IBMInputValueError: If an instruction does not contain a box.
            IBMInputValueError: If an instruction contains a box without twirl annotation.
            IBMInputValueError: If an instruction contains unphysical qubits, i.e., qubits that do not
                belong to the "physical" register ``QuantumRegister(backend.num_qubits, 'q')`` for the
                backend in use.
            IBMInputValueError: If an instruction a box with non-ISA gates.
            IBMInputValueError: If an instruction cannot be learned by any of the supported learning
                protocols.
        """
        if target := getattr(self._backend, "target", None):
            for instruction in instructions:
                validate_instruction(instruction, target)

        if configuration := getattr(self._backend, "configuration", None):
            validate_options(self.options, configuration())

        inputs = noise_learner_v3_inputs_to_0_1(instructions, self.options).model_dump()
        inputs["version"] = 3  # TODO: this is a work-around for the dispatch
        runtime_options = self.options.to_runtime_options()
        runtime_options["backend"] = self._backend.name

        if self._session:
            run = self._session._run
        else:
            run = self._service._run
            runtime_options["instance"] = self._backend._instance

            if get_cm_session():
                logger.warning(
                    "Even though a session/batch context manager is open this job will run in job "
                    "mode because the %s primitive was initialized outside the context manager. "
                    "Move the %s initialization inside the context manager to run in a "
                    "session/batch.",
                    self._PROGRAM_ID,
                    self._PROGRAM_ID,
                )

        return run(
            program_id=self._PROGRAM_ID,
            options=runtime_options,
            inputs=inputs,
            result_decoder=self._DECODER,
            calibration_id=getattr(self._backend, "calibration_id", None),
        )

    def backend(self) -> BackendV2:
        """Return the backend the primitive query will be run on."""
        return self._backend
