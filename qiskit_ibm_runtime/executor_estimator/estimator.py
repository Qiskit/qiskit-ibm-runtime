# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Executor-based EstimatorV2 primitive."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, get_args

from qiskit.primitives.base import BaseEstimatorV2
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from ..base_primitive import get_mode_service_backend
from ..executor import Executor
from ..fake_provider.local_service import QiskitRuntimeLocalService
from ..options_models.estimator import EstimatorOptions
from .finalize_options import finalize_estimator_options
from .prepare import prepare
from .utils import BoxType, find_box_type, find_unique_layers

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction
    from qiskit.primitives.containers.estimator_pub import EstimatorPubLike
    from qiskit.providers import BackendV2

    from ..batch import Batch
    from ..fake_provider.local_runtime_job import LocalRuntimeJob
    from ..runtime_job_v2 import RuntimeJobV2
    from ..session import Session

logger = logging.getLogger(__name__)


class EstimatorV2(BaseEstimatorV2):
    """Executor-based EstimatorV2 primitive for IBM Quantum Compute (formerly Qiskit Runtime).

    This is an implementation of EstimatorV2 built on top of the Executor primitive,
    enabling transparent client-side processing with faster feedback loops and greater
    user control.

    Example:
        .. code-block:: python

            from qiskit import QuantumCircuit
            from qiskit.quantum_info import SparsePauliOp
            from qiskit_ibm_runtime import QiskitRuntimeService
            from qiskit_ibm_runtime.executor_estimator import EstimatorV2

            service = QiskitRuntimeService()
            backend = service.least_busy(operational=True, simulator=False)

            # Create a simple circuit
            circuit = QuantumCircuit(2)
            circuit.h(0)
            circuit.cx(0, 1)

            # Define observable
            observable = SparsePauliOp.from_list([("ZZ", 1), ("XX", 1)])

            # Run the estimator with options
            estimator = EstimatorV2(mode=backend)
            estimator.options.default_precision = 0.01
            estimator.options.execution.init_qubits = True
            job = estimator.run([(circuit, observable)])
            result = job.result()

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`~qiskit.providers.BackendV2` if you are using job mode.
            * A :class:`~qiskit_ibm_runtime.Session` if you are using session execution mode.
            * A :class:`~qiskit_ibm_runtime.Batch` if you are using batch execution mode.

            Refer to the `IBM Quantum Compute documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`__
            for more information about execution modes.

        options: Estimator options.
            See
            :class:`~qiskit_ibm_runtime.options_models.estimator.EstimatorOptions`
            for all available options.
    """

    options: EstimatorOptions
    """The options of this Estimator."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: EstimatorOptions | dict | None = None,
    ):
        super().__init__()

        # Store mode, service, and backend for simulator detection
        self._mode, self._service, self._backend = get_mode_service_backend(mode)

        # Coerced to `EstimatorOptions` via `__setattr__()`.
        self.options = options if options is not None else EstimatorOptions()  # type: ignore[assignment]

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute ``name`` to ``value``.

        Handle ``options`` as a special case, ensuring it is set to an ``EstimatorOptions``
        instance. This is an alternative to using ``@setter``, as the setter causes issues in
        ``ipython`` autocomplete features.
        """
        if name == "options":
            if isinstance(value, dict):
                value = EstimatorOptions(**value)
            elif not isinstance(value, EstimatorOptions):
                raise TypeError(f"Expected EstimatorOptions or dict, got {type(value)}")

        super().__setattr__(name, value)

    def find_unique_layers(
        self, pubs: Iterable[EstimatorPubLike], types: Literal["gates", "all"] = "gates"
    ) -> list[CircuitInstruction]:
        """Return the unique boxed layers found across the given PUBs.

        The ``types`` of layers can be either ``"gates"`` or ``"all"``, corresponding to only
        gate layers or all layers, respectively. The returned list then contains one instance of
        each distinct boxed layer (represented as a :class:`~.CircuitInstruction`) appearing
        in the input PUBs.

        For example, for noise learning, keep only the qubit gate layers:

        .. code-block:: python

            est = EstimatorV2(mode, options)
            est.options.resilience.pec_mitigation = True

            layers = est.find_unique_layers(pubs, types="gates")

            results = NoiseLearnerV3(mode).run(layers).result()
            pauli_linblad_maps = results.to_pauli_lindblad_maps()

            # Assign the learned model so PEC uses it on the next run.
            est.options.resilience.layer_noise_model = zip(layers, pauli_linblad_maps)

        Args:
            pubs: The list of PUBs to return a list of unique boxes for.
            types: The types of layers to return. Can be either ``"gates"`` or ``"all"``.

        Returns:
            The unique boxed layers of a certain type found across the given PUBs.
        """
        coerced_pubs = [EstimatorPub.coerce(pub, None) for pub in pubs]
        options = self.finalize_options()
        layers = find_unique_layers(
            pubs=coerced_pubs,
            twirling_options=options.twirling,
            measure_noise_learning=options.resilience.measure_noise_learning,
            inject_noise=options.resilience.pec_mitigation
            or (options.resilience.zne_mitigation and options.resilience.zne.amplifier == "pea"),
            add_tags=True,
        )
        box_types = get_args(BoxType) if types == "all" else ("gates",)
        return [layer for layer in layers if find_box_type(layer) in box_types]

    def finalize_options(self) -> EstimatorOptions:
        """Construct and finalize the Estimator options.

        This method combines the configured resilience level with the user-provided option to
        produce the final :class:`~qiskit_ibm_runtime.options_models.EstimatorOptions` instance
        used inside a call to :meth:`~.Estimator.run`.

        The process used to produce the finalized options is as follows:

        1. Initialize a new :class:`~qiskit_ibm_runtime.options_models.EstimatorOptions` object with
           defaults determined by
           :attr:`~qiskit_ibm_runtime.options_models.EstimatorOptions.resilience_level`.
        2. Apply user-specified options, skipping the fields left as ``None`` that are intended to
           inherit the resilience-level defaults.
        3. Enforce required option dependencies. Specifically:

           * Enabling measurement mitigation automatically enables measurement twirling.
           * Enabling gate-based mitigation techniques (such as PEA-based ZNE or PEC) automatically
             enables both gate and measurement twirling.

        Returns:
            The finalized :class:`~qiskit_ibm_runtime.options_models.EstimatorOptions` object.
        """
        return finalize_estimator_options(self.options)

    def run(
        self, pubs: Iterable[EstimatorPubLike], *, precision: float | None = None
    ) -> RuntimeJobV2 | LocalRuntimeJob:
        """Submit a request to the estimator primitive.

        For moderate and complex workloads, the client-side processing done to map estimator inputs
        to executor inputs can be resource intensive and cause a delay between invoking the function
        and the ``job`` being submitted. In order to check the progress of the call, it is
        recommended to setup logging (with an ``INFO`` level) - see
        `IBM Quantum Compute documentation
        <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-service#logging>`__
        for more information.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                and observables or tuples ``(circuit, observables, parameter_values)``.
            precision: The target precision for expectation value estimates of each
                estimator pub that does not specify its own precision. If ``None``,
                the value from ``options.default_precision`` will be used.

        Returns:
            The submitted job.

        Raises:
            ValueError: If backend is not provided.
            IBMInputValueError: If no pubs are provided, if precision is not properly
                specified, or if unsupported options are detected.
        """
        # Pre-process: Convert Estimator input into a QuantumProgram
        logger.info("Starting pre-processing")
        quantum_program, executor_options = prepare(
            pubs,
            self.options,
            precision,
            add_tags=isinstance(self._service, QiskitRuntimeLocalService),
            backend=self._backend,
        )

        # Set semantic role for post-processing dispatch
        quantum_program._semantic_role = "estimator_v2"

        executor = Executor(mode=self._backend, options=executor_options)

        logger.info(
            "Submitting %d pub%s to executor with %d total shots",
            len(quantum_program.items),
            "s" if len(quantum_program.items) > 1 else "",
            quantum_program.shots * sum(item.size() for item in quantum_program.items),
        )

        return executor.run(quantum_program)
