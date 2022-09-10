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

"""Qiskit Runtime flexible session."""

from typing import Dict, Optional, Type, Union
from types import TracebackType
from functools import wraps

from qiskit_ibm_runtime import QiskitRuntimeService
from .runtime_job import RuntimeJob
from .runtime_program import ParameterNamespace
from .program.result_decoder import ResultDecoder
from .ibm_backend import IBMBackend
from .utils.converters import hms_to_seconds


def _active_session(func):  # type: ignore
    """Decorator used to ensure the session is active."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):  # type: ignore
        if not self._active:
            raise RuntimeError("The session is closed.")
        return func(self, *args, **kwargs)

    return _wrapper


class Session:
    """Class for creating a flexible Qiskit Runtime session.

    A Qiskit Runtime ``session`` allows you to group a collection of iterative calls to
    the quantum computer. A session is started when the first job within the session
    is started. Subsequent jobs within the session are prioritized by the scheduler.
    Data used within a session, such as transpiled circuits, is also cached to avoid
    unnecessary overhead.

    You can open a Qiskit Runtime session using this ``Session`` class and submit jobs
    to one or more primitives.

    For example::

        from qiskit.test.reference_circuits import ReferenceCircuits
        from qiskit_ibm_runtime import Sampler, Session, Options

        options = Options(optimization_level=3)

        with Session(backend="ibmq_qasm_simulator") as session:
            sampler = Sampler(session=session, options=options)
            job = sampler.run(circ)
            print(f"Sampler job ID: {job.job_id()}")
            print(f"Sampler job result:" {job.result()})
    """

    def __init__(
        self,
        service: Optional[QiskitRuntimeService] = None,
        backend: Optional[Union[str, IBMBackend]] = None,
        max_time: Optional[Union[int, str]] = None,
    ):
        """Session constructor.

        Args:
            service: Optional instance of the ``QiskitRuntimeService`` class,
                defaults to ``QiskitRuntimeService()`` which tries to initialize
                your default saved account.
            backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                string name of backend. If not specified, a backend will be selected
                automatically (IBM Cloud channel only).
            max_time: (EXPERIMENTAL setting, can break between releases without warning)
                Maximum amount of time, a runtime session can be open before being
                forcibly closed. Can be specified as seconds (int) or a string like "2h 30m 40s".

        Raises:
            ValueError: If an input value is invalid.
        """

        self._service = service or QiskitRuntimeService()

        if self._service.channel == "ibm_quantum" and not backend:
            raise ValueError('"backend" is required for ``ibm_quantum`` channel.')
        if isinstance(backend, IBMBackend):
            backend = backend.name
        self._backend = backend

        self._session_id: Optional[str] = None
        self._active = True

        self._max_time = (
            max_time
            if max_time is None or isinstance(max_time, int)
            else hms_to_seconds(max_time, "Invalid max_time value: ")
        )

    @_active_session
    def run(
        self,
        program_id: str,
        inputs: Union[Dict, ParameterNamespace],
        options: Optional[Dict] = None,
        result_decoder: Optional[Type[ResultDecoder]] = None,
    ) -> RuntimeJob:
        """Run a program in the session.

        Args:
            program_id: Program ID.
            inputs: Program input parameters. These input values are passed
                to the runtime program.
            options: Runtime options that control the execution environment.

                * image: the runtime image used to execute the program, specified in
                  the form of ``image_name:tag``. Not all accounts are
                  authorized to select a different image.
                * log_level: logging level to set in the execution environment. The valid
                  log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
                  The default level is ``WARNING``.

        Returns:
            Submitted job.
        """

        # TODO: Cache data when server supports it.

        # TODO: Do we really need to specify a None max time if session has started?
        max_time = self._max_time if not self._session_id else None
        options = options or {}
        options["backend"] = self._backend

        job = self._service.run(
            program_id=program_id,
            options=options,
            inputs=inputs,
            session_id=self._session_id,
            start_session=self._session_id is None,
            max_execution_time=max_time,
            result_decoder=result_decoder,
        )

        if self._session_id is None:
            self._session_id = job.job_id()

        if self._backend is None:
            self._backend = job.backend().name

        return job

    def close(self) -> None:
        """Close the session."""
        self._active = False
        if self._session_id:
            self._service._api_client.close_session(self._session_id)

    def backend(self) -> Optional[str]:
        """Return backend for this session.

        Returns:
            Backend for this session. None if unknown.
        """
        return self._backend

    @property
    def session_id(self) -> str:
        """Return the session ID.

        Returns:
            Session ID.
        """
        return self._session_id

    @property
    def service(self) -> QiskitRuntimeService:
        """Return service associated with this session.

        Returns:
            :class:`qiskit_ibm_runtime.QiskitRuntimeService` associated with this session.
        """
        return self._service

    def __enter__(self) -> "Session":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()


# Default session
_DEFAULT_SESSION: Optional[Session] = None


def get_default_session(
    service: Optional[QiskitRuntimeService] = None,
    backend: Optional[Union[str, IBMBackend]] = None,
) -> Session:
    """Return the default session.

    Args:
        service: Service to use to create a default session.
        backend: Backend for the default session.
    """
    if service is None:
        service = (
            backend.service
            if isinstance(backend, IBMBackend)
            else QiskitRuntimeService()
        )
    if isinstance(backend, IBMBackend):
        backend = backend.name

    global _DEFAULT_SESSION  # pylint: disable=global-statement
    if (
        _DEFAULT_SESSION is None
        or not _DEFAULT_SESSION._active
        or _DEFAULT_SESSION._backend != backend
        or (service is not None and _DEFAULT_SESSION.service.channel != service.channel)
    ):
        if _DEFAULT_SESSION and _DEFAULT_SESSION._active:
            _DEFAULT_SESSION.close()
        _DEFAULT_SESSION = Session(service=service, backend=backend)
    return _DEFAULT_SESSION
