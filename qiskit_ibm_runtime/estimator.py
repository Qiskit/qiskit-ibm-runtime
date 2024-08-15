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

"""Estimator primitive."""

from __future__ import annotations

from typing import Optional, Dict, Union, Iterable
import logging

from qiskit.providers import BackendV1, BackendV2

from qiskit.primitives.base import BaseEstimatorV2
from qiskit.primitives.containers import EstimatorPubLike
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from .runtime_job_v2 import RuntimeJobV2
from .options.estimator_options import EstimatorOptions
from .base_primitive import BasePrimitiveV2
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg
from .utils.qctrl import validate_v2 as qctrl_validate_v2
from .utils import validate_estimator_pubs

# pylint: disable=unused-import,cyclic-import
from .session import Session
from .batch import Batch

logger = logging.getLogger(__name__)


class Estimator:
    """Base class for Qiskit Runtime Estimator."""

    version = 0


class EstimatorV2(BasePrimitiveV2[EstimatorOptions], Estimator, BaseEstimatorV2):
    r"""Class for interacting with Qiskit Runtime Estimator primitive service.

    Qiskit Runtime Estimator primitive service estimates expectation values of quantum circuits and
    observables.

    The :meth:`run` can be used to submit circuits, observables, and parameters
    to the Estimator primitive.

    Following construction, an estimator is used by calling its :meth:`run` method
    with a list of PUBs (Primitive Unified Blocs). Each PUB contains four values that, together,
    define a computation unit of work for the estimator to complete:

    * a single :class:`~qiskit.circuit.QuantumCircuit`, possibly parametrized, whose final state we
      define as :math:`\psi(\theta)`,

    * one or more observables (specified as any :class:`~.ObservablesArrayLike`, including
      :class:`~.Pauli`, :class:`~.SparsePauliOp`, ``str``) that specify which expectation values to
      estimate, denoted :math:`H_j`, and

    * a collection parameter value sets to bind the circuit against, :math:`\theta_k`.

    * an optional target precision for expectation value estimates.

    Here is an example of how the estimator is used.

    .. code-block:: python

        from qiskit.circuit.library import RealAmplitudes
        from qiskit.quantum_info import SparsePauliOp
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, EstimatorV2 as Estimator

        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)

        psi = RealAmplitudes(num_qubits=2, reps=2)
        hamiltonian = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        theta = [0, 1, 1, 2, 3, 5]

        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_psi = pm.run(psi)
        isa_observables = hamiltonian.apply_layout(isa_psi.layout)

        estimator = Estimator(backend=backend)

        # calculate [ <psi(theta1)|hamiltonian|psi(theta)> ]
        job = estimator.run([(isa_psi, isa_observables, [theta])])
        pub_result = job.result()[0]
        print(f"Expectation values: {pub_result.data.evs}")
    """

    _options_class = EstimatorOptions

    version = 2

    def __init__(
        self,
        mode: Optional[Union[BackendV1, BackendV2, Session, Batch, str]] = None,
        backend: Optional[Union[str, BackendV1, BackendV2]] = None,
        session: Optional[Session] = None,
        options: Optional[Union[Dict, EstimatorOptions]] = None,
    ):
        """Initializes the Estimator primitive.

        Args:
            mode: The execution mode used to make the primitive query. It can be:

                * A :class:`Backend` if you are using job mode.
                * A :class:`Session` if you are using session execution mode.
                * A :class:`Batch` if you are using batch execution mode.

                Refer to the
                `Qiskit Runtime documentation <https://docs.quantum.ibm.com/guides/execution-modes>`_.
                for more information about the ``Execution modes``.

            backend: (DEPRECATED) Backend to run the primitive. This can be a backend name
                or an :class:`IBMBackend` instance. If a name is specified, the default account
                (e.g. ``QiskitRuntimeService()``) is used.

            session: (DEPRECATED) Session in which to call the primitive.

                If both ``session`` and ``backend`` are specified, ``session`` takes precedence.
                If neither is specified, and the primitive is created inside a
                :class:`qiskit_ibm_runtime.Session` context manager, then the session is used.
                Otherwise if IBM Cloud channel is used, a default backend is selected.

            options: Estimator options, see :class:`EstimatorOptions` for detailed description.

        Raises:
            NotImplementedError: If "q-ctrl" channel strategy is used.
        """
        BaseEstimatorV2.__init__(self)
        Estimator.__init__(self)
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
            )
        if mode is None:
            mode = session if backend and session else backend if backend else session
        BasePrimitiveV2.__init__(self, mode=mode, options=options)

    def run(
        self, pubs: Iterable[EstimatorPubLike], *, precision: float | None = None
    ) -> RuntimeJobV2:
        """Submit a request to the estimator primitive.

        Args:
            pubs: An iterable of pub-like (primitive unified bloc) objects, such as
                tuples ``(circuit, observables)`` or ``(circuit, observables, parameter_values)``.
            precision: The target precision for expectation value estimates of each
                run Estimator Pub that does not specify its own precision. If None
                the estimator's default precision value will be used.

        Returns:
            Submitted job.

        Raises:
            ValueError: if precision value is not strictly greater than 0.
        """
        if precision is not None:
            if precision <= 0:
                raise ValueError("The precision value must be strictly greater than 0.")
        coerced_pubs = [EstimatorPub.coerce(pub, precision) for pub in pubs]
        validate_estimator_pubs(coerced_pubs)
        return self._run(coerced_pubs)  # type: ignore[arg-type]

    def _validate_options(self, options: dict) -> None:
        """Validate that primitive inputs (options) are valid

        Raises:
            ValidationError: if validation fails.
            ValueError: if validation fails.
        """

        if self._service._channel_strategy == "q-ctrl":
            qctrl_validate_v2(options)
            return

        if (
            options.get("resilience", {}).get("pec_mitigation", False) is True
            and self._backend is not None
            and self._backend.configuration().simulator is True
            and not options["simulator"]["coupling_map"]
        ):
            raise ValueError(
                "When the backend is a simulator and pec_mitigation is enabled, "
                "a coupling map is required."
            )

        if options.get("optimization_level", None):
            issue_deprecation_msg(
                msg="The 'optimization_level' option is deprecated",
                version="0.25.0",
                remedy="Instead, you can perform circuit optimization using Qiskit transpiler "
                "or Qiskit transpiler service. "
                "See https://docs.quantum.ibm.com/guides/transpile for more information.",
            )

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "estimator"
