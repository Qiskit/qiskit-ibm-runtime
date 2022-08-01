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
from .runtime_options import RuntimeOptions
from .settings import Transpilation, Resilience
from .program.result_decoder import ResultDecoder
from .sampler import Sampler
from .estimator import Estimator
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

    The ``Session`` class allows you to open a "session" with the Qiskit Runtime service.
    Jobs submitted during a session get prioritized scheduling. This class allows
    you to submit jobs to one or more of the primitives. For example::

        from qiskit.test.reference_circuits import ReferenceCircuits

        with Session() as session:
            sampler = session.sampler()
            sampler.options.backend = "ibmq_qasm_simulator"
            sampler.settings.transpilation.optimization_level = 1
            job = sampler.run(circ)
            print(f"Job ID: {job.job_id}")
            print(job.result())
    """

    def __init__(
        self,
        service: Optional[QiskitRuntimeService] = None,
        max_time: Optional[Union[int, str]] = None,
    ):
        """Session constructor.
        Args:
            service: Optional instance of :class:`qiskit_ibm_runtime.QiskitRuntimeService` class,
                defaults to `QiskitRuntimeService()` which tries to initialize your default saved account.
            max_time: (EXPERIMENTAL setting, can break between releases without warning)
                Maximum amount of time, a runtime session can be open before being
                forcibly closed. Can be specified as seconds (int) or a string like "2h 30m 40s".
        """

        self._service = service or QiskitRuntimeService()
        self._session_id: Optional[str] = None
        self._active = True

        self._max_time = max_time if max_time is None or isinstance(max_time, int) \
            else hms_to_seconds(max_time, "Invalid max_time value: ")

    @_active_session
    def run(
        self,
        program_id: str,
        inputs: Union[Dict, ParameterNamespace],
        options: Optional[Union[RuntimeOptions, Dict]] = None,
        result_decoder: Optional[Type[ResultDecoder]] = None,
    ) -> RuntimeJob:
        """Run a program in the session.

        Args:
            program_id: Program ID.
            inputs: Program input parameters. These input values are passed
                to the runtime program.
            options: Runtime options that control the execution environment. See
                :class:`RuntimeOptions` for all available options.

        Returns:
            Submitted job.
        """

        # TODO: Cache data when server supports it.

        # TODO: Do we really need to specify a None max time if session has started?
        max_time = self._max_time if not self._session_id else None

        job = self._service.run(
            program_id=program_id,
            options=options,
            inputs=inputs,
            session_id=self._session_id,
            start_session=self._session_id is None,
            max_execution_time=max_time,
            result_decoder=result_decoder
        )

        if self._session_id is None:
            self._session_id = job.job_id

        return job

    def sampler(
        self,
        options: Optional[Union[Dict, RuntimeOptions]] = None,
        transpilation_settings: Optional[Union[Dict, Transpilation]] = None,
        resilience_settings: Optional[Union[Dict, Resilience]] = None,
    ) -> Sampler:
        """Return an instance of the Sampler primitive.

        Args:

            options: Runtime options dictionary that control the execution environment:

                * backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                    string name of backend, if not specified a backend will be selected
                    automatically (IBM Cloud only).
                * image: the runtime image used to execute the program, specified in
                    the form of ``image_name:tag``. Not all accounts are
                    authorized to select a different image.
                * log_level: logging level to set in the execution environment. The valid
                    log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
                    The default level is ``WARNING``.

            transpilation_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Qiskit transpiler settings. The transpilation process converts
                operations in the circuit to those supported by the backend, swaps qubits with the
                circuit to overcome limited qubit connectivity and some optimizations to reduce the
                circuit's gate count where it can.

                * optimization_level: How much optimization to perform on the circuits.
                    Higher levels generate more optimized circuits,
                    at the expense of longer transpilation times.
                    * 0: no optimization
                    * 1: light optimization (default)
                    * 2: heavy optimization
                    * 3: even heavier optimization

            resilience_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Using these settings allows you to build resilient algorithms by
                leveraging the state of the art error suppression, mitigation and correction techniques.

                * level: How much resilience to build against errors.
                    Higher levels generate more accurate results,
                    at the expense of longer processing times.
                    * 0: no resilience (default)
                    * 1: light resilience
        """
        return Sampler(
            service=self._service,
            options=options,
            transpilation_settings=transpilation_settings,
            resilience_settings=resilience_settings,
            session=self
            )

    def estimator() -> Estimator:
        raise NotImplementedError("Under construction")

    def close(self) -> None:
        """Close the session."""
        self._active = False
        if self._session_id:
            self._service._api_client.close_session(self._session_id)

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
