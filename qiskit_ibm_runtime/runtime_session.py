# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit runtime session."""

from typing import Dict, Any, Optional, Type, Union
from types import TracebackType
import copy
from functools import wraps
from dataclasses import asdict

from qiskit_ibm_runtime import qiskit_runtime_service  # pylint: disable=unused-import
from .runtime_job import RuntimeJob
from .runtime_program import ParameterNamespace
from .runtime_options import RuntimeOptions
from .program.result_decoder import ResultDecoder


def _active_session(func):  # type: ignore
    """Decorator used to ensure the session is active."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):  # type: ignore
        if not self._active:
            raise RuntimeError("The session is closed.")
        return func(self, *args, **kwargs)

    return _wrapper


class RuntimeSession:
    """Runtime Session"""

    def __init__(
        self,
        service: "qiskit_runtime_service.QiskitRuntimeService",
        program_id: str,
        inputs: Union[Dict, ParameterNamespace],
        options: Optional[Union[RuntimeOptions, Dict]] = None,
        max_time: Optional[int] = None,
    ):
        """RuntimeSession constructor.
        Args:
            service: Runtime service.
            program_id: Program ID.
            inputs: Initial program inputs.
            options: Runtime options.
            max_time: (DEPRECATED) Maximum amount of time, a runtime session can
                be open before being forcibly closed.
        """
        self._service = service
        self._program_id = program_id
        self._options: dict = options
        if isinstance(options, RuntimeOptions):
            self._options = asdict(options)
        if max_time:
            self._options["max_execution_time"] = max_time
        self._initial_inputs = inputs
        self._initial_job: Optional[RuntimeJob] = None
        self._job: Optional[RuntimeJob] = None
        self._session_id: Optional[str] = None
        self._active = True
        self._start_session = True

    @_active_session
    def write(self, **kwargs: Dict) -> None:
        """Write to the session."""
        if self._session_id is None:
            inputs = copy.copy(self._initial_inputs)
        else:
            inputs = {}
        inputs.update(kwargs)
        if self._session_id is None:
            self._start_session = True
            self._initial_job = self._run(inputs=inputs)
            self._job = self._initial_job
            self._session_id = self._job.job_id()
        else:
            self._start_session = False
            self._options["max_execution_time"] = None
            self._job = self._run(inputs=inputs)

    def _run(self, inputs: Union[Dict, ParameterNamespace]) -> RuntimeJob:
        """Run a program"""
        return self._service.run(
            program_id=self._program_id,
            options=self._options,
            inputs=inputs,
            session_id=self._session_id,
            start_session=self._start_session,
        )

    @_active_session
    def read(
        self,
        timeout: Optional[float] = None,
        decoder: Optional[Type[ResultDecoder]] = None,
    ) -> Any:
        """Read from the session.
        Args:
            timeout: Number of seconds to wait for job.
            decoder: A :class:`ResultDecoder` subclass used to decode job results.
        Returns:
            Data returned from the session.
        """
        return self._job.result(timeout=timeout, decoder=decoder)

    def info(self) -> Dict:
        """Return session information.
        Returns:
            Session information.
        """
        out = {}
        if self._options:
            out["backend"] = self._options["backend"] or "unknown"  # type: ignore
        if self._job:
            out["job_id"] = self._job.job_id()
            out["job_status"] = self._job.status()
            out["backend"] = self._job.backend
        return out

    def close(self) -> None:
        """Close the session."""
        self._active = False
        if self._session_id:
            self._service._api_client.close_session(self._session_id)

    def __enter__(self) -> "RuntimeSession":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()
