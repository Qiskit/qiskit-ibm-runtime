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
from copy import deepcopy
from typing import TYPE_CHECKING, Any

import numpy as np
from qiskit.primitives.base import BaseEstimatorV2
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from ..base_primitive import get_mode_service_backend
from ..exceptions import IBMInputValueError
from ..executor import Executor
from ..executor.dynamical_decoupling import apply_dynamical_decoupling
from ..fake_provider.local_service import QiskitRuntimeLocalService
from ..options_models.converters import estimator_options_to_executor_options
from ..options_models.estimator import EstimatorOptions
from .pec.prepare_pec import prepare_pec
from .prepare import prepare
from .prepare_pea import prepare_pea
from .utils import find_unique_layers, resolve_precision
from .zne.prepare_zne import prepare_zne

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction
    from qiskit.primitives.containers.estimator_pub import EstimatorPubLike
    from qiskit.providers import BackendV2

    from ..batch import Batch
    from ..runtime_job_v2 import RuntimeJobV2
    from ..session import Session

logger = logging.getLogger(__name__)

RESILIENCE_LEVEL_DEFAULTS = {
    0: {
        "enable_gates": False,
        "enable_measure": False,
        "measure_mitigation": False,
        "zne_mitigation": False,
    },
    1: {
        "enable_gates": False,
        "enable_measure": True,
        "measure_mitigation": True,
        "zne_mitigation": False,
    },
    2: {
        "enable_gates": True,
        "enable_measure": True,
        "measure_mitigation": True,
        "zne_mitigation": True,
    },
}
"""Default configuration for resilience levels used to finalize estimator options.

Fields:
* ``enable_gates``: Whether to enable twirling for gates.
* ``enable_measure``: Whether to enable twirling for measurements.
* ``measure_mitigation``: Whether to apply measurement error mitigation.
* ``zne_mitigation``: Whether to apply zero-noise extrapolation (ZNE).
"""


class EstimatorV2(BaseEstimatorV2):
    """Executor-based EstimatorV2 primitive for Qiskit Runtime.

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

            Refer to the `Qiskit Runtime documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
            for more information about execution modes.

        options: Estimator options.
            See
            :class:`~qiskit_ibm_runtime.options_models.estimator_options.EstimatorOptions`
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

        # Only create executor for non-local backends
        # For local simulators (QiskitRuntimeLocalService), we'll use BackendEstimatorV2 directly
        self._executor = None
        if not isinstance(self._service, QiskitRuntimeLocalService):
            self._executor = Executor(mode=mode)

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

    def find_unique_layers(self, pubs: Iterable[EstimatorPubLike]) -> list[CircuitInstruction]:
        """Return the unique boxed layers found across the given PUBs.

        The returned list contains one instance of each distinct boxed layer (represented as a
        :class:`~.CircuitInstruction`) appearing in the input PUBs. This list can be passed
        directly to the :meth:`~.qiskit_ibm_runtime.noise_learner_v3.NoiseLearnerV3.run` method
        for characterization, avoiding redundant learning of identical layers.

        Args:
            pubs: The list of PUBs to return a list of unique boxes for.

        Returns:
            The unique boxed layers found across the given PUBs.
        """
        coerced_pubs = [EstimatorPub.coerce(pub, None) for pub in pubs]
        options = self.finalize_options()
        return find_unique_layers(
            pubs=coerced_pubs,
            twirling_options=options.twirling,
            measure_noise_learning=options.resilience.measure_noise_learning,
            inject_noise=options.resilience.pec_mitigation
            or (options.resilience.zne_mitigation and options.resilience.zne.amplifier == "pea"),
        )

    def finalize_options(self) -> EstimatorOptions:
        """Construct and finalize the runtime estimator options.

        This method combines the configured resilience level with the user-provided option
        to produce the final :class:`~.EstimatorOptions` instance used inside a call to
        :meth:`~.Estimator.run`.

        The process used to produce the finalized options is as follows:

        1. Initialize a new :class:`~.EstimatorOptions` object with defaults determined by
            :attr:`~.EstimatorOptions.resilience_level`.
        2. Apply user-specified options, skipping the fields left as ``None`` that are intended to
            inherit the resilience-level defaults.
        3. Enforce required option dependencies. Specifically:
            * Enabling measurement mitigation automatically enables measurement twirling.
            * Enabling gate-based mitigation techniques (such as PEA-based ZNE or PEC) automatically
              enables both gate and measurement twirling.

        Returns:
            The finalized :class:`~.EstimatorOptions` object.
        """
        finalized_options = deepcopy(self.options)

        # Begin by initializing options based on resilience level
        defaults = RESILIENCE_LEVEL_DEFAULTS[finalized_options.resilience_level]

        if finalized_options.twirling.enable_gates is None:
            finalized_options.twirling.enable_gates = defaults["enable_gates"]
        if finalized_options.twirling.enable_measure is None:
            finalized_options.twirling.enable_measure = defaults["enable_measure"]
        if finalized_options.resilience.measure_mitigation is None:
            finalized_options.resilience.measure_mitigation = defaults["measure_mitigation"]
        if finalized_options.resilience.zne_mitigation is None:
            finalized_options.resilience.zne_mitigation = defaults["zne_mitigation"]

        # Force-set some values based on mitigation
        if finalized_options.resilience.measure_mitigation is True:
            finalized_options.twirling.enable_measure = True
        if (
            finalized_options.resilience.zne_mitigation is True
            and finalized_options.resilience.zne.amplifier == "pea"
        ):
            finalized_options.twirling.enable_gates = True
            finalized_options.twirling.enable_measure = True
        if finalized_options.resilience.pec_mitigation is True:
            finalized_options.twirling.enable_gates = True
            finalized_options.twirling.enable_measure = True

        return finalized_options

    def run(
        self, pubs: Iterable[EstimatorPubLike], *, precision: float | None = None
    ) -> RuntimeJobV2:
        """Submit a request to the estimator primitive.

        For moderate and complex workloads, the client-side processing done to map estimator inputs
        to executor inputs can be resource intensive and cause a delay between invoking the function
        and the ``job`` being submitted. In order to check the progress of the call, it is
        recommended to setup logging (with an ``INFO`` level) - see
        `Qiskit Runtime documentation
        <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-service#logging>`_
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
        # Coerce pubs to EstimatorPub objects
        coerced_pubs = [EstimatorPub.coerce(pub, precision) for pub in pubs]
        if not coerced_pubs:
            raise IBMInputValueError("No pubs provided. At least one pub is required.")

        # Finalize the options dynamically by:
        #   * Generating new options according to the specified resilience level
        #   * Combining these options with the user-provided options
        #   * Enforcing required dependencies between option values
        options = self.finalize_options()

        # Convert pubs to QuantumProgram and map options using the selected prepare function
        logger.info("Starting pre-processing")

        resolved_precision = resolve_precision(coerced_pubs, precision)
        if resolved_precision is not None:
            shots = int(np.ceil(1.0 / (resolved_precision**2)))
        elif options.default_shots is not None:
            shots = int(options.default_shots)
        else:
            shots = int(np.ceil(1.0 / (options.default_precision**2)))

        # Check if we're in local simulator mode
        if self._executor is None:
            logger.info("Running in local simulator mode")

            options_dict = options.model_dump()
            options_dict["default_shots"] = shots

            return self._service._run(
                program_id="estimator",
                inputs={"pubs": coerced_pubs, "options": options_dict},
                options={"backend": self._backend},
                calibration_id=None,
            )

        if options.dynamical_decoupling.enable:
            for pub in coerced_pubs:
                if pub.circuit.has_control_flow_op():
                    raise IBMInputValueError(
                        "Dynamical decoupling is not compatible with dynamic circuits "
                        "(circuits with control flow operations)."
                    )

        if options.resilience.pec_mitigation and options.resilience.zne_mitigation:
            raise IBMInputValueError(
                "PEC mitigation and ZNE mitigation are incompatible with one another."
            )

        # Route to appropriate prepare function
        if options.resilience.pec_mitigation:
            if options.resilience.noise_model_mapping is None:
                raise IBMInputValueError(
                    "When PEC mitigation is enabled, you must provide a noise model "
                    "via options.resilience.noise_model_mapping"
                )
            quantum_program = prepare_pec(
                pubs=coerced_pubs,
                twirling_options=options.twirling,
                shots=shots,
                pec_options=options.resilience.pec,
                noise_model_mapping=options.resilience.noise_model_mapping,
                measure_noise_learning=options.resilience.measure_noise_learning
                if options.resilience.measure_mitigation
                else None,
            )
        elif options.resilience.zne_mitigation:
            if options.resilience.zne.amplifier == "pea":
                quantum_program = prepare_pea(
                    pubs=coerced_pubs,
                    twirling_options=options.twirling,
                    shots=shots,
                    zne_options=options.resilience.zne,
                    noise_model_mapping=options.resilience.noise_model_mapping or {},
                    measure_noise_learning=options.resilience.measure_noise_learning
                    if options.resilience.measure_mitigation
                    else None,
                )
            else:
                quantum_program = prepare_zne(
                    pubs=coerced_pubs,
                    twirling_options=options.twirling,
                    shots=shots,
                    zne_options=options.resilience.zne,
                    measure_noise_learning=options.resilience.measure_noise_learning
                    if options.resilience.measure_mitigation
                    else None,
                )
        else:
            quantum_program = prepare(
                pubs=coerced_pubs,
                twirling_options=options.twirling,
                shots=shots,
                measure_noise_learning=options.resilience.measure_noise_learning
                if options.resilience.measure_mitigation
                else None,
            )

        if options.dynamical_decoupling.enable:
            quantum_program = apply_dynamical_decoupling(
                backend=self._backend,
                dd_options=options.dynamical_decoupling,
                quantum_program=quantum_program,
            )
        # Serialize options (assuming passthrough is correctly configured)
        quantum_program.passthrough_data["post_processor"]["options"] = {  # type: ignore[index, call-overload]
            "twirling": self.options.twirling.model_dump(),
            "dynamical_decoupling": self.options.dynamical_decoupling.model_dump(),
            "resilience": self.options.resilience.model_dump(exclude={"noise_model_mapping"}),
        }

        # Set executor options
        self._executor.options = estimator_options_to_executor_options(options)

        # Submit to executor
        logger.info(
            "Submitting %d pub%s to executor with %d shots",
            len(coerced_pubs),
            "s" if len(coerced_pubs) > 1 else "",
            quantum_program.shots,
        )

        return self._executor.run(quantum_program)
