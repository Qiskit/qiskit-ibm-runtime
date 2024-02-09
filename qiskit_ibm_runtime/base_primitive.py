# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Base class for Qiskit Runtime primitives."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Union
import copy
import logging
from dataclasses import asdict
import warnings

from qiskit.providers.options import Options as TerraOptions

from .provider_session import get_cm_session as get_cm_provider_session

from .options import Options
from .options.utils import set_default_error_levels
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .utils.default_session import get_cm_session
from .constants import DEFAULT_DECODERS
from .qiskit_runtime_service import QiskitRuntimeService

# pylint: disable=unused-import,cyclic-import
from .session import Session

logger = logging.getLogger(__name__)


class BasePrimitive(ABC):
    """Base class for Qiskit Runtime primitives."""

    def __init__(
        self,
        backend: Optional[Union[str, IBMBackend]] = None,
        session: Optional[Union[Session, str, IBMBackend]] = None,
        options: Optional[Union[Dict, Options]] = None,
    ):
        """Initializes the primitive.

        Args:

            backend: Backend to run the primitive. This can be a backend name or an :class:`IBMBackend`
                instance. If a name is specified, the default account (e.g. ``QiskitRuntimeService()``)
                is used.

            session: Session in which to call the primitive.

                If both ``session`` and ``backend`` are specified, ``session`` takes precedence.
                If neither is specified, and the primitive is created inside a
                :class:`qiskit_ibm_runtime.Session` context manager, then the session is used.
                Otherwise if IBM Cloud channel is used, a default backend is selected.

            options: Primitive options, see :class:`Options` for detailed description.
                The ``backend`` keyword is still supported but is deprecated.

        Raises:
            ValueError: Invalid arguments are given.
        """
        # `self._options` in this class is a Dict.
        # The base class, however, uses a `_run_options` which is an instance of
        # qiskit.providers.Options. We largely ignore this _run_options because we use
        # a nested dictionary to categorize options.
        self._session: Optional[Session] = None
        self._service: QiskitRuntimeService = None
        self._backend: Optional[IBMBackend] = None

        if options is None:
            self._options = asdict(Options())
        elif isinstance(options, Options):
            self._options = asdict(copy.deepcopy(options))
        else:
            options_copy = copy.deepcopy(options)
            default_options = asdict(Options())
            self._options = Options._merge_options(default_options, options_copy)

        if isinstance(session, Session):
            self._session = session
            self._service = self._session.service
            self._backend = self._service.backend(
                name=self._session.backend(), instance=self._session._instance
            )
            return
        elif session is not None:
            raise ValueError("session must be of type Session or None")

        if isinstance(backend, IBMBackend):
            self._service = backend.service
            self._backend = backend
        elif isinstance(backend, str):
            self._service = (
                QiskitRuntimeService()
                if QiskitRuntimeService.global_service is None
                else QiskitRuntimeService.global_service
            )
            self._backend = self._service.backend(backend)
        elif get_cm_session():
            self._session = get_cm_session()
            self._service = self._session.service
            self._backend = self._service.backend(
                name=self._session.backend(), instance=self._session._instance
            )
        else:
            self._service = (
                QiskitRuntimeService()
                if QiskitRuntimeService.global_service is None
                else QiskitRuntimeService.global_service
            )
            if self._service.channel != "ibm_cloud":
                raise ValueError(
                    "A backend or session must be specified when not using ibm_cloud channel."
                )
        # Check if initialized within a IBMBackend session. If so, issue a warning.
        if get_cm_provider_session():
            warnings.warn(
                "A Backend.run() session is open but Primitives will not be run within this session"
            )

    def _run_primitive(self, primitive_inputs: Dict, user_kwargs: Dict) -> RuntimeJob:
        """Run the primitive.

        Args:
            primitive_inputs: Inputs to pass to the primitive.
            user_kwargs: Individual options to overwrite the default primitive options.

        Returns:
            Submitted job.
        """
        combined = Options._merge_options(self._options, user_kwargs)

        if self._backend:
            combined = set_default_error_levels(
                combined,
                self._backend,
                Options._DEFAULT_OPTIMIZATION_LEVEL,
                Options._DEFAULT_RESILIENCE_LEVEL,
            )
        else:
            combined["optimization_level"] = Options._DEFAULT_OPTIMIZATION_LEVEL
            combined["resilience_level"] = Options._DEFAULT_RESILIENCE_LEVEL

        self._validate_options(combined)

        combined = Options._set_default_resilience_options(combined)
        combined = Options._remove_none_values(combined)

        primitive_inputs.update(Options._get_program_inputs(combined))

        if self._backend and combined["transpilation"]["skip_transpilation"]:
            for circ in primitive_inputs["circuits"]:
                self._backend.check_faulty(circ)

        logger.info("Submitting job using options %s", combined)

        runtime_options = Options._get_runtime_options(combined)
        if self._session:
            return self._session.run(
                program_id=self._program_id(),
                inputs=primitive_inputs,
                options=runtime_options,
                callback=combined.get("environment", {}).get("callback", None),
                result_decoder=DEFAULT_DECODERS.get(self._program_id()),
            )

        if self._backend:
            runtime_options["backend"] = self._backend.name
            if "instance" not in runtime_options:
                runtime_options["instance"] = self._backend._instance

        return self._service.run(
            program_id=self._program_id(),
            options=runtime_options,
            inputs=primitive_inputs,
            callback=combined.get("environment", {}).get("callback", None),
            result_decoder=DEFAULT_DECODERS.get(self._program_id()),
        )

    @property
    def session(self) -> Optional[Session]:
        """Return session used by this primitive.

        Returns:
            Session used by this primitive, or ``None`` if session is not used.
        """
        return self._session

    @property
    def options(self) -> TerraOptions:
        """Return options values for the sampler.

        Returns:
            options
        """
        return TerraOptions(**self._options)

    def set_options(self, **fields: Any) -> None:
        """Set options values for the sampler.

        Args:
            **fields: The fields to update the options
        """
        self._options = Options._merge_options(self._options, fields)

    @abstractmethod
    def _validate_options(self, options: dict) -> None:
        """Validate that program inputs (options) are valid

        Raises:
            ValueError: if resilience_level is out of the allowed range.
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        raise NotImplementedError()
