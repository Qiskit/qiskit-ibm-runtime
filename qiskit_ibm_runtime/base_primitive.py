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

from qiskit.providers.options import Options as TerraOptions

from .options import Options
from .options.utils import set_default_error_levels
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .session import get_cm_session
from .constants import DEFAULT_DECODERS
from .qiskit_runtime_service import QiskitRuntimeService
from .utils.deprecation import issue_deprecation_msg

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
        elif isinstance(session, IBMBackend):
            issue_deprecation_msg(
                msg="Passing a backend instance as the ``session`` parameter is deprecated",
                version="0.10.0",
                remedy="Please pass it as the ``backend`` parameter instead.",
            )
            self._service = session.service
            self._backend = session
        elif isinstance(session, str):
            issue_deprecation_msg(
                msg="Passing a backend name as the ``session`` parameter is deprecated",
                version="0.10.0",
                remedy="Please pass it as the ``backend`` parameter instead.",
            )
            self._service = QiskitRuntimeService()
            self._backend = self._service.backend(session)
        elif isinstance(backend, Session):
            issue_deprecation_msg(
                msg="``session`` is no longer the first parameter when initializing "
                "a Qiskit Runtime primitive",
                version="0.10.0",
                remedy="Please use ``session=session`` instead.",
            )
            self._session = backend
            self._service = self._session.service
            self._backend = self._service.backend(
                name=self._session.backend(), instance=self._session._instance
            )
        elif isinstance(backend, IBMBackend):
            self._service = backend.service
            self._backend = backend
        elif isinstance(backend, str):
            self._service = QiskitRuntimeService()
            self._backend = self._service.backend(backend)
        elif get_cm_session():
            self._session = get_cm_session()
            self._service = self._session.service
            self._backend = self._service.backend(
                name=self._session.backend(), instance=self._session._instance
            )
        else:
            self._service = QiskitRuntimeService()
            if self._service.channel != "ibm_cloud":
                raise ValueError(
                    "A backend or session must be specified when not using ibm_cloud channel."
                )

        # self._first_run = True
        # self._circuits_map = {}
        # if self.circuits:
        #     for circuit in self.circuits:
        #         circuit_id = _hash(
        #             json.dumps(_circuit_key(circuit), cls=RuntimeEncoder)
        #         )
        #         if circuit_id not in self._session._circuits_map:
        #             self._circuits_map[circuit_id] = circuit
        #             self._session._circuits_map[circuit_id] = circuit

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
