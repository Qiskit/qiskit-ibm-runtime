# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
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

from dataclasses import asdict
from typing import Any, Dict, Iterable, Optional, Union
import logging

from qiskit.circuit import QuantumCircuit
from qiskit.providers import BackendV1, BackendV2
from qiskit.primitives.containers import EstimatorPubLike
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from .constants import DEFAULT_DECODERS
from .runtime_job_v2 import RuntimeJobV2
from .ibm_backend import IBMBackend
from .options.estimator_options import EstimatorOptions
from .options.noise_learner_options import NoiseLearnerOptions
from .options.utils import remove_dict_unset_values, remove_empty_dict
from .utils import validate_isa_circuits
from .utils.utils import is_simulator

from .fake_provider.local_service import QiskitRuntimeLocalService
from .qiskit_runtime_service import QiskitRuntimeService
from .provider_session import get_cm_session


# pylint: disable=unused-import,cyclic-import
from .session import Session
from .batch import Batch

logger = logging.getLogger(__name__)


class NoiseLearner:
    """Class for executing noise learning experiments.

    The noise learner allows characterizing the noise processes affecting the gates in one or more
    circuits of interest, based on the Pauli-Lindblad noise model described in [1].

    The :meth:`run` allows runnig a noise learner job for a list of circuits. After the job is
    submitted, the gates are collected into independent layers, and subsequently the resulting layers are
    are characterized individually. The way in which the gates are collected into layers depends on the
    ``twirling_strategy`` specified in the given ``options`` (see :class:`NoiseLearnerOptions` for more
    details).

    Here is an example of how the estimator is used.

    .. code-block:: python

        from qiskit.circuit import QuantumCircuit
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, NoiseLearner

        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)

        # a two-qubit GHZ circuit
        ghz = QuantumCircuit(2)
        ghz.h(0)
        ghz.cx(0, 1)

        # another two-qubit GHZ circuit
        another_ghz = QuantumCircuit(3)
        another_ghz.h(0)
        another_ghz.cx(0, 1)
        another_ghz.cx(1, 2)
        another_ghz.cx(0, 1)

        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        circuits = pm.run([ghz, another_ghz])

        # run the noise learner job
        learner = NoiseLearner(backend, options)
        job = learner.run(circuits)

    References:
        1. E. van den Berg, Z. Minev, A. Kandala, K. Temme, *Probabilistic error
           cancellation with sparse Pauli–Lindblad models on noisy quantum processors*,
           Nature Physics volume 19, pages1116–1121 (2023).
           `arXiv:2201.09866 [quant-ph] <https://arxiv.org/abs/2201.09866>`_

    """

    def __init__(
        self,
        mode: Optional[Union[BackendV1, BackendV2, Session, Batch, str]] = None,
        options: Optional[Union[Dict, NoiseLearnerOptions, EstimatorOptions]] = None,
    ):
        """Initializes the noise learner.

        Args:
            mode: The execution mode used to make the primitive query. It can be:

                * A :class:`Backend` if you are using job mode.
                * A :class:`Session` if you are using session execution mode.
                * A :class:`Batch` if you are using batch execution mode.

                Refer to the `Qiskit Runtime documentation <https://docs.quantum.ibm.com/run>`_.
                for more information about the ``Execution modes``.

            backend: Backend to run the primitive. This can be a backend name or an :class:`IBMBackend`
                instance. If a name is specified, the default account (e.g. ``QiskitRuntimeService()``)
                is used.

            session: Session in which to call the primitive.

                If both ``session`` and ``backend`` are specified, ``session`` takes precedence.
                If neither is specified, and the primitive is created inside a
                :class:`qiskit_ibm_runtime.Session` context manager, then the session is used.
                Otherwise if IBM Cloud channel is used, a default backend is selected.

            options: :class:`NoiseLearnerOptions`. Alternatively, :class:`EstimatorOptions` can be
                provided, in which case the estimator options get reformatted into noise learner options
                and all the irrelevant fields are ignored.
        """
        self._mode: Optional[Union[Session, Batch]] = None
        self._service: QiskitRuntimeService | QiskitRuntimeLocalService = None
        self._backend: Optional[BackendV1 | BackendV2] = None

        if isinstance(mode, (Session, Batch)):
            self._mode = mode
            self._service = self._mode.service
            self._backend = self._mode._backend
        elif isinstance(mode, IBMBackend):  # type: ignore[unreachable]
            self._service = mode.service
            self._backend = mode
        elif isinstance(mode, (BackendV1, BackendV2)):
            self._service = QiskitRuntimeLocalService()
            self._backend = mode
        elif isinstance(mode, str):
            self._service = (
                QiskitRuntimeService()
                if QiskitRuntimeService.global_service is None
                else QiskitRuntimeService.global_service
            )
            self._backend = self._service.backend(mode)
        elif get_cm_session():
            self._mode = get_cm_session()  # type: ignore[assignment]
            self._service = self._mode.service
            self._backend = self._service.backend(  # type: ignore
                name=self._mode.backend(), instance=self._mode._instance
            )
        else:
            raise ValueError("A backend or session must be specified.")

        self._set_options(options)

    @property
    def options(self) -> NoiseLearnerOptions:
        """The options in this noise learner."""
        return self._options

    def run(self, tasks: Iterable[Union[QuantumCircuit, EstimatorPubLike]]) -> RuntimeJobV2:
        """Submit a request to the noise learner program.

        Args:
            tasks: An iterable of circuits to run the noise learner program for. Alternatively,
                pub-like (primitive unified bloc) objects can be specified, such as
                tuples ``(circuit, observables)`` or ``(circuit, observables, parameter_values)``.
                In this case, the pub-like objects are converted to a list of circuits, and all
                the other fields (such as ``observables`` and ``parameter_values``) are ignored.

        Returns:
            Submitted job.

        """
        if not all(isinstance(t, QuantumCircuit) for t in tasks):
            coerced_pubs = [EstimatorPub.coerce(pub) for pub in tasks]
            tasks = [p.circuit for p in coerced_pubs]

        # Store learner-specific and runtime options in different dictionaries
        options_dict = asdict(self.options)
        learner_options = {"options": self._get_inputs_options(options_dict)}
        runtime_options = NoiseLearnerOptions._get_runtime_options(options_dict)

        # Define the program inputs
        inputs = {"circuits": tasks}
        inputs.update(learner_options)

        if self._backend:
            for task in tasks:
                if getattr(self._backend, "target", None) and not is_simulator(self._backend):
                    validate_isa_circuits([task], self._backend.target)

                if isinstance(self._backend, IBMBackend):
                    self._backend.check_faulty(task)

        logger.info("Submitting job using options %s", learner_options)

        # Batch or Session
        if self._mode:
            return self._mode.run(
                program_id=self._program_id(),
                inputs=inputs,
                options=runtime_options,
                callback=options_dict.get("environment", {}).get("callback", None),
                result_decoder=DEFAULT_DECODERS.get(self._program_id()),
            )

        if self._backend:
            runtime_options["backend"] = self._backend
            if "instance" not in runtime_options and isinstance(self._backend, IBMBackend):
                runtime_options["instance"] = self._backend._instance

        if isinstance(self._service, QiskitRuntimeService):
            return self._service.run(
                program_id=self._program_id(),
                options=runtime_options,
                inputs=inputs,
                callback=options_dict.get("environment", {}).get("callback", None),
                result_decoder=DEFAULT_DECODERS.get(self._program_id()),
            )

        return self._service.run(
            program_id=self._program_id(),  # type: ignore[arg-type]
            options=runtime_options,
            inputs=inputs,
        )

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "noise-learner"

    def _set_options(
        self, options: Optional[Union[Dict, NoiseLearnerOptions, EstimatorOptions]] = None
    ) -> None:
        """
        Sets the options, ensuring that they are of type ``NoiseLearnerOptions``.
        """
        if not options:
            self._options = NoiseLearnerOptions()
        elif isinstance(options, NoiseLearnerOptions):
            self._options = options
        elif isinstance(options, EstimatorOptions):
            options_d = asdict(options.resilience.layer_noise_learning)  # type: ignore[union-attr]
            options_d.update({"twirling_strategy": options.twirling.strategy})  # type: ignore[union-attr]
            options_d.update({"max_execution_time": options.max_execution_time})
            self._options = NoiseLearnerOptions(**options_d)
        else:
            self._options = NoiseLearnerOptions(**options)

    @staticmethod
    def _get_inputs_options(options_dict: dict[str, Any]) -> dict[str, str]:
        """Returns a dictionary of options that must be included in the program inputs,
        filtering out every option that is not part of the NoiseLearningOptions."""
        ret = {}

        for key in [
            "max_layers_to_learn",
            "shots_per_randomization",
            "num_randomizations",
            "layer_pair_depths",
            "twirling_strategy",
            "simulator",
        ]:
            if key in options_dict:
                ret[key] = options_dict[key]

        remove_dict_unset_values(ret)
        remove_empty_dict(ret)

        return ret
