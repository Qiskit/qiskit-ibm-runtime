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

from typing import Dict, Optional, Type, Union, Callable
from types import TracebackType
from functools import wraps

from qiskit.circuit import QuantumCircuit

from qiskit_ibm_runtime import QiskitRuntimeService
from .runtime_job import RuntimeJob
from .runtime_program import ParameterNamespace
from .program.result_decoder import ResultDecoder
from .ibm_backend import IBMBackend
from .utils.converters import hms_to_seconds
from .utils.deprecation import issue_deprecation_msg
from .exceptions import IBMInputValueError


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
            # Close the session only if all jobs are finished and
            # you don't need to run more in the session.
            session.close()
    """

    def __init__(
        self,
        service: Optional[QiskitRuntimeService] = None,
        backend: Optional[Union[str, IBMBackend]] = None,
        max_time: Optional[Union[int, str]] = None,
    ):  # pylint: disable=line-too-long
        """Session constructor.

        Args:
            service: Optional instance of the ``QiskitRuntimeService`` class.
                If ``None``, the service associated with the backend, if known, is used.
                Otherwise ``QiskitRuntimeService()`` is used to initialize
                your default saved account.
            backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                string name of backend. An instance of :class:`qiskit_ibm_provider.IBMBackend` will not work.
                If not specified, a backend will be selected automatically (IBM Cloud channel only).

            max_time: (EXPERIMENTAL setting, can break between releases without warning)
                Maximum amount of time, a runtime session can be open before being
                forcibly closed. Can be specified as seconds (int) or a string like "2h 30m 40s".
                This value must be in between 300 seconds and the
                `system imposed maximum
                <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/faqs/max_execution_time.html>`_.

        Raises:
            ValueError: If an input value is invalid.
        """

        if service is None:
            self._service = (
                backend.service
                if isinstance(backend, IBMBackend)
                else QiskitRuntimeService()
            )
        else:
            self._service = service

        if self._service.channel == "ibm_quantum" and not backend:
            raise ValueError('"backend" is required for ``ibm_quantum`` channel.')
        if isinstance(backend, IBMBackend):
            backend = backend.name
        self._backend = backend

        self._session_id: Optional[str] = None
        self._active = True

        self._circuits_map: Dict[str, QuantumCircuit] = {}

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
        callback: Optional[Callable] = None,
        result_decoder: Optional[Type[ResultDecoder]] = None,
    ) -> RuntimeJob:
        """Run a program in the session.

        Args:
            program_id: Program ID.
            inputs: Program input parameters. These input values are passed
                to the runtime program.
            options: Runtime options that control the execution environment.
                See :class:`qiskit_ibm_runtime.RuntimeOptions` for all available options,
                EXCEPT ``backend``, which should be specified during session initialization.
            callback: Callback function to be invoked for any interim results and final result.

        Returns:
            Submitted job.

        Raises:
            IBMInputValueError: If a backend is passed in through options that does not match
                the current session backend.
        """

        options = options or {}
        if "backend" in options:
            issue_deprecation_msg(
                "'backend' is no longer a supported option within a session",
                "0.9",
                "Instead, specify a backend when creating a Session instance.",
                3,
            )
            if self._backend and options["backend"] != self._backend:
                raise IBMInputValueError(
                    f"The backend '{options['backend']}' is different from",
                    f"the session backend '{self._backend}'",
                )
        else:
            options["backend"] = self._backend

        if not self._session_id:
            # TODO: What happens if session max time != first job max time?
            # Use session max time if this is first job.
            options["max_execution_time"] = self._max_time

        job = self._service.run(
            program_id=program_id,
            options=options,
            inputs=inputs,
            session_id=self._session_id,
            start_session=self._session_id is None,
            callback=callback,
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
            Session ID. None until a job runs in the session.
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
        set_cm_session(self)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        set_cm_session(None)


# Default session
_DEFAULT_SESSION: Optional[Session] = None
_IN_SESSION_CM = False


def set_cm_session(session: Optional[Session]) -> None:
    """Set the context manager session."""
    global _DEFAULT_SESSION  # pylint: disable=global-statement
    global _IN_SESSION_CM  # pylint: disable=global-statement
    _DEFAULT_SESSION = session
    _IN_SESSION_CM = session is not None


def get_default_session(
    service: Optional[QiskitRuntimeService] = None,
    backend: Optional[Union[str, IBMBackend]] = None,
) -> Session:
    """Return the default session.

    Args:
        service: Service to use to create a default session.
        backend: Backend for the default session.
    """
    backend_name = backend.name if isinstance(backend, IBMBackend) else backend

    global _DEFAULT_SESSION  # pylint: disable=global-statement
    session = _DEFAULT_SESSION
    if (  # pylint: disable=too-many-boolean-expressions
        _DEFAULT_SESSION is None
        or not _DEFAULT_SESSION._active
        or (backend_name is not None and _DEFAULT_SESSION._backend != backend_name)
        or (service is not None and _DEFAULT_SESSION.service.channel != service.channel)
    ):
        # Create a new session if one doesn't exist, or if the user wants to switch backend/channel.
        # Close the session only if all jobs are finished and you don't need to run more in the session.
        if _DEFAULT_SESSION and not _IN_SESSION_CM and _DEFAULT_SESSION._active:
            _DEFAULT_SESSION.close()
        if service is None:
            service = (
                backend.service
                if isinstance(backend, IBMBackend)
                else QiskitRuntimeService()
            )
        session = Session(service=service, backend=backend)
        if not _IN_SESSION_CM:
            _DEFAULT_SESSION = session
    return session
