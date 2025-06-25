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

from qiskit.providers import BackendV2

from qiskit.primitives.base import BaseEstimatorV2
from qiskit.primitives.containers import EstimatorPubLike
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from .runtime_job_v2 import RuntimeJobV2
from .options.estimator_options import EstimatorOptions
from .base_primitive import BasePrimitiveV2
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

        from qiskit.circuit.library import real_amplitudes
        from qiskit.quantum_info import SparsePauliOp
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, EstimatorV2 as Estimator

        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)

        psi = real_amplitudes(num_qubits=2, reps=2)
        hamiltonian = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        theta = [0, 1, 1, 2, 3, 5]

        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_psi = pm.run(psi)
        isa_observables = hamiltonian.apply_layout(isa_psi.layout)

        estimator = Estimator(mode=backend)

        # calculate [ <psi(theta1)|hamiltonian|psi(theta)> ]
        job = estimator.run([(isa_psi, isa_observables, [theta])])
        pub_result = job.result()[0]
        print(f"Expectation values: {pub_result.data.evs}")
    """

    _options_class = EstimatorOptions

    version = 2

    def __init__(
        self,
        mode: Optional[Union[BackendV2, Session, Batch, str]] = None,
        options: Optional[Union[Dict, EstimatorOptions]] = None,
    ):
        """Initializes the Estimator primitive.

        Args:
            mode: The execution mode used to make the primitive query. It can be:

                * A :class:`Backend` if you are using job mode.
                * A :class:`Session` if you are using session execution mode.
                * A :class:`Batch` if you are using batch execution mode.

                Refer to the
                `Qiskit Runtime documentation
                <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_.
                for more information about the ``Execution modes``.

            options: Estimator options, see :class:`EstimatorOptions` for detailed description.

        """
        BaseEstimatorV2.__init__(self)
        Estimator.__init__(self)

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

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "estimator"
