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

"""Sampler primitive."""

from __future__ import annotations
import os
from typing import Dict, Optional, Sequence, Any, Union, Iterable
import logging

from qiskit.circuit import QuantumCircuit
from qiskit.primitives import BaseSampler
from qiskit.primitives.base import BaseSamplerV2
from qiskit.primitives.containers.sampler_pub import SamplerPub, SamplerPubLike
from qiskit.providers import BackendV1, BackendV2

from .options import Options
from .runtime_job import RuntimeJob
from .runtime_job_v2 import RuntimeJobV2
from .ibm_backend import IBMBackend
from .base_primitive import BasePrimitiveV1, BasePrimitiveV2

# pylint: disable=unused-import,cyclic-import
from .session import Session
from .batch import Batch
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg
from .utils.qctrl import validate as qctrl_validate
from .utils.qctrl import validate_v2 as qctrl_validate_v2
from .utils import validate_classical_registers
from .options import SamplerOptions

logger = logging.getLogger(__name__)


class Sampler:
    """Base type for Sampler."""

    version = 0


class SamplerV2(BasePrimitiveV2[SamplerOptions], Sampler, BaseSamplerV2):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    This class supports version 2 of the Sampler interface, which uses different
    input and output formats than version 1.

    Qiskit Runtime Sampler primitive returns the sampled result according to the
    specified output type. For example, it returns a bitstring for each shot
    if measurement level 2 (bits) is requested.

    The :meth:`run` method can be used to submit circuits and parameters to the Sampler primitive.
    """

    _options_class = SamplerOptions

    version = 2

    def __init__(
        self,
        mode: Optional[Union[BackendV1, BackendV2, Session, Batch, str]] = None,
        backend: Optional[Union[str, BackendV1, BackendV2]] = None,
        session: Optional[Session] = None,
        options: Optional[Union[Dict, SamplerOptions]] = None,
    ):
        """Initializes the Sampler primitive.

        Args:
            mode: The execution mode used to make the primitive query. It can be:

                * A :class:`Backend` if you are using job mode.
                * A :class:`Session` if you are using session execution mode.
                * A :class:`Batch` if you are using batch execution mode.

                Refer to the `Qiskit Runtime documentation <https://docs.quantum.ibm.com/run>`_.
                for more information about the ``Execution modes``.

            backend: (DEPRECATED) Backend to run the primitive. This can be a backend name or
                an :class:`IBMBackend` instance. If a name is specified, the default account
                (e.g. ``QiskitRuntimeService()``) is used.

            session: (DEPRECATED) Session in which to call the primitive.

                If both ``session`` and ``backend`` are specified, ``session`` takes precedence.
                If neither is specified, and the primitive is created inside a
                :class:`qiskit_ibm_runtime.Session` context manager, then the session is used.
                Otherwise if IBM Cloud channel is used, a default backend is selected.

            options: Sampler options, see :class:`SamplerOptions` for detailed description.

        Raises:
            NotImplementedError: If "q-ctrl" channel strategy is used.
        """
        self.options: SamplerOptions
        BaseSamplerV2.__init__(self)
        Sampler.__init__(self)
        if backend:
            deprecate_arguments(
                "backend",
                "0.24.0",
                "Please use the 'mode' parameter instead.",
            )
        if session:
            deprecate_arguments(
                "session",
                "0.24.0",
                "Please use the 'mode' parameter instead.",
            )
        if isinstance(mode, str) or isinstance(backend, str):
            issue_deprecation_msg(
                "The backend name as execution mode input has been deprecated.",
                "0.24.0",
                "A backend object should be provided instead. Get the backend directly from"
                " the service using `QiskitRuntimeService().backend('ibm_backend')`",
                3,
            )
            issue_deprecation_msg(
                msg="Passing a backend as a string is deprecated",
                version="0.26.0",
                remedy="Use the actual backend object instead.",
                period="3 months",
                stacklevel=2,
            )

        if mode is None:
            mode = session if backend and session else backend if backend else session
        BasePrimitiveV2.__init__(self, mode=mode, options=options)

    def run(self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None) -> RuntimeJobV2:
        """Submit a request to the sampler primitive.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                  or tuples ``(circuit, parameter_values)``.
            shots: The total number of shots to sample for each sampler pub that does
                   not specify its own shots. If ``None``, the primitive's default
                   shots value will be used, which can vary by implementation.

        Returns:
            Submitted job.
            The result of the job is an instance of
            :class:`qiskit.primitives.containers.PrimitiveResult`.

        Raises:
            ValueError: Invalid arguments are given.
        """
        coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

        validate_classical_registers(coerced_pubs)

        return self._run(coerced_pubs)  # type: ignore[arg-type]

    def _validate_options(self, options: dict) -> None:
        """Validate that primitive inputs (options) are valid

        Raises:
            ValidationError: if validation fails.
        """

        if self._service._channel_strategy == "q-ctrl":
            qctrl_validate_v2(options)
            return

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "sampler"


class SamplerV1(BasePrimitiveV1, Sampler, BaseSampler):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    .. deprecated:: 0.23
       The ``SamplerV1`` primitives have been deprecated in 0.23, released on April 15, 2024.
       See the `V2 migration guide <https://docs.quantum.ibm.com/api/migration-guides/v2-primitives>`_.
       for more details.
       The ``SamplerV1`` support will be removed no earlier than July 15, 2024.

    Qiskit Runtime Sampler primitive service calculates quasi-probability distribution
    of bitstrings from quantum circuits.

    The :meth:`run` method can be used to submit circuits and parameters to the Sampler primitive.

    You are encouraged to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitives. Jobs submitted within a session
    are prioritized by the scheduler.

    Example::

        from qiskit.circuit import QuantumCircuit, QuantumRegister, ClassicalRegister
        from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler

        service = QiskitRuntimeService(channel="ibm_cloud")

        # Bell Circuit
        qr = QuantumRegister(2, name="qr")
        cr = ClassicalRegister(2, name="cr")
        qc = QuantumCircuit(qr, cr, name="bell")
        qc.h(qr[0])
        qc.cx(qr[0], qr[1])
        qc.measure(qr, cr)

        with Session(service, backend="ibmq_qasm_simulator") as session:
            sampler = Sampler(session=session)

            job = sampler.run(qc, shots=1024)
            print(f"Job ID: {job.job_id()}")
            print(f"Job result: {job.result()}")

            # You can run more jobs inside the session
    """

    _options_class = Options

    version = 1

    def __init__(
        self,
        backend: Optional[Union[str, IBMBackend]] = None,
        session: Optional[Session] = None,
        options: Optional[Union[Dict, Options]] = None,
    ):
        """Initializes the Sampler primitive.

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
        """
        # `self._options` in this class is a Dict.
        # The base class, however, uses a `_run_options` which is an instance of
        # qiskit.providers.Options. We largely ignore this _run_options because we use
        # a nested dictionary to categorize options.
        BaseSampler.__init__(self)
        Sampler.__init__(self)
        BasePrimitiveV1.__init__(self, backend=backend, session=session, options=options)

    def run(  # pylint: disable=arguments-differ
        self,
        circuits: QuantumCircuit | Sequence[QuantumCircuit],
        parameter_values: Sequence[float] | Sequence[Sequence[float]] | None = None,
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive.

        Args:
            circuits: A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameter_values: Concrete parameters to be bound.
            **kwargs: Individual options to overwrite the default primitive options.

        Returns:
            Submitted job.
            The result of the job is an instance of :class:`qiskit.primitives.SamplerResult`.

        Raises:
            ValueError: Invalid arguments are given.
        """
        # To bypass base class merging of options.
        user_kwargs = {"_user_kwargs": kwargs}
        return super().run(
            circuits=circuits,
            parameter_values=parameter_values,
            **user_kwargs,
        )

    def _run(  # pylint: disable=arguments-differ
        self,
        circuits: Sequence[QuantumCircuit],
        parameter_values: Sequence[Sequence[float]],
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive.

        Args:
            circuits: A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameter_values: An optional list of concrete parameters to be bound.
            **kwargs: Individual options to overwrite the default primitive options.

        Returns:
            Submitted job.
        """
        inputs = {
            "circuits": circuits,
            "parameters": [circ.parameters for circ in circuits],
            "parameter_values": parameter_values,
        }
        return self._run_primitive(
            primitive_inputs=inputs, user_kwargs=kwargs.get("_user_kwargs", {})
        )

    def _validate_options(self, options: dict) -> None:
        """Validate that primitive inputs (options) are valid
        Raises:
            ValueError: if resilience_level is out of the allowed range.
        """
        if os.getenv("QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"):
            return

        if self._service._channel_strategy == "q-ctrl":
            qctrl_validate(options)
            return

        valid_levels = list(range(Options._MAX_RESILIENCE_LEVEL_SAMPLER + 1))
        if options.get("resilience_level") and not options.get("resilience_level") in valid_levels:
            raise ValueError(
                f"resilience_level {options.get('resilience_level')} is not a valid value."
                f"It can only take the values {valid_levels} in Sampler."
            )
        Options.validate_options(options)

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "sampler"
