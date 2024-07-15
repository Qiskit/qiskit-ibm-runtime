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
import os
from dataclasses import asdict
from typing import Optional, Dict, Sequence, Any, Union, Iterable
import logging

from qiskit.circuit import QuantumCircuit
from qiskit.providers import BackendV1, BackendV2
from qiskit.quantum_info.operators.base_operator import BaseOperator
from qiskit.quantum_info.operators import SparsePauliOp
from qiskit.primitives import BaseEstimator
from qiskit.primitives.base import BaseEstimatorV2
from qiskit.primitives.containers import EstimatorPubLike
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from .runtime_job import RuntimeJob
from .runtime_job_v2 import RuntimeJobV2
from .ibm_backend import IBMBackend
from .options import Options
from .options.estimator_options import EstimatorOptions
from .options.noise_learner_options import NoiseLearnerOptions
from .base_primitive import BasePrimitiveV1, BasePrimitiveV2
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg
from .utils.qctrl import validate as qctrl_validate
from .utils.qctrl import validate_v2 as qctrl_validate_v2
from .utils import validate_estimator_pubs

from .fake_provider.local_service import QiskitRuntimeLocalService
from .qiskit_runtime_service import QiskitRuntimeService
from .provider_session import get_cm_session 


# pylint: disable=unused-import,cyclic-import
from .session import Session
from .batch import Batch

logger = logging.getLogger(__name__)


class NoiseLearner:
    """Noise learner."""
    
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
            self._mode = get_cm_session()
            self._service = self._mode.service
            self._backend = self._service.backend(  # type: ignore
                name=self._mode.backend(), instance=self._mode._instance
            )
        else:
            raise ValueError("A backend or session must be specified.")

        self._set_options(options)

    def _set_options(self, options: Optional[Union[Dict, NoiseLearnerOptions, EstimatorOptions]] = None):
        """
        Sets the options, ensuring that they are of type ``NoiseLearnerOptions``.
        """
        if not options:
            self._options = NoiseLearnerOptions()
        elif isinstance(options, NoiseLearnerOptions):
            self._options = options
        elif isinstance(options, EstimatorOptions):
            options_d = asdict(options.resilience.layer_noise_learning)
            options_d.update({"twirling_strategy": options.twirling.strategy})
            options_d.update({"max_execution_time": options.max_execution_time})
            self._options = NoiseLearnerOptions(**options_d)
        else:
            self._options = NoiseLearnerOptions(**options)

    @property
    def options(self) -> NoiseLearnerOptions:
        """The options in this noise learner."""
        return self._options
    
    def run(self, tasks: Iterable[QuantumCircuit, EstimatorPubLike]) -> RuntimeJobV2:
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
        if not all([isinstance(t, QuantumCircuit) for t in tasks]):
            coerced_pubs = [EstimatorPub.coerce(pub) for pub in tasks]
            tasks = [p.circuit for p in coerced_pubs]