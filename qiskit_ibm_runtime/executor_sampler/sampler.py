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

"""Executor-based SamplerV2 primitive."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Literal

from qiskit.primitives.base import BaseSamplerV2
from qiskit.primitives.containers.sampler_pub import SamplerPub
from samplomatic import InjectNoise, Tag
from samplomatic.utils import get_annotation

from ..base_primitive import get_mode_service_backend
from ..executor import Executor
from ..executor_estimator.utils import find_unique_layers
from ..fake_provider.local_service import QiskitRuntimeLocalService
from ..options_models.sampler import SamplerOptions
from .prepare import prepare

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from qiskit.circuit import CircuitInstruction
    from qiskit.primitives.containers.sampler_pub import SamplerPubLike
    from qiskit.providers import BackendV2

    from ..batch import Batch
    from ..runtime_job_v2 import RuntimeJobV2
    from ..session import Session


logger = logging.getLogger(__name__)


class SamplerV2(BaseSamplerV2):
    """Executor-based Sampler primitive for IBM Quantum Compute (formerly Qiskit Runtime).

    This is an implementation of SamplerV2 built on top of the Executor primitive,
    enabling transparent client-side processing with faster feedback loops and greater
    user control.

    **Limitations:**

    - When twirling is disabled, circuits must not contain :class:`~qiskit.circuit.BoxOp`
      instructions.
    - Dynamical decoupling is incompatible with dynamic circuits.

    Example:
        .. code-block:: python

            from qiskit import QuantumCircuit
            from qiskit_ibm_runtime import QiskitRuntimeService
            from qiskit_ibm_runtime.executor_sampler import SamplerV2

            service = QiskitRuntimeService()
            backend = service.least_busy(operational=True, simulator=False)

            # Create a simple circuit
            circuit = QuantumCircuit(2, 2)
            circuit.h(0)
            circuit.cx(0, 1)
            circuit.measure_all()

            # Run the sampler with options
            sampler = SamplerV2(mode=backend)
            sampler.options.default_shots = 2048
            sampler.options.execution.init_qubits = True
            job = sampler.run([circuit])
            result = job.result()

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`~qiskit.providers.BackendV2` if you are using job mode.
            * A :class:`~qiskit_ibm_runtime.Session` if you are using session execution mode.
            * A :class:`~qiskit_ibm_runtime.Batch` if you are using batch execution mode.

            Refer to the `IBM Quantum Compute documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
            for more information about execution modes.

        options: Sampler options. See :class:`~qiskit_ibm_runtime.options_models.SamplerOptions`
            for all available options.
    """

    options: SamplerOptions
    """The options of this Sampler."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: SamplerOptions | dict | None = None,
    ):
        super().__init__()

        # Store mode, service, and backend for simulator detection
        self._mode, self._service, self._backend = get_mode_service_backend(mode)

        # Coerced to `SamplerOptions` via `__setattr__()`.
        self.options = options if options is not None else SamplerOptions()  # type: ignore[assignment]

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute ``name`` to ``value``.

        Handle ``options`` as a special case, ensuring it is set to an ``SamplerOptions`` instance.
        This is an alternative to using ``@setter``, as the setter causes issues in ``ipython``
        autocomplete features.
        """
        if name == "options":
            if isinstance(value, dict):
                value = SamplerOptions(**value)
            elif not isinstance(value, SamplerOptions):
                raise TypeError(f"Expected SamplerOptions or dict, got {type(value)}")

        super().__setattr__(name, value)

    def find_unique_layers(
        self, pubs: Iterable[SamplerPubLike], types: Literal["gates", "all"] = "gates"
    ) -> list[CircuitInstruction]:
        """Return the unique boxed layers found across the given PUBs of a given type.

        The ``types`` of layers can be either ``"gates"`` or ``"all"``, corresponding to only
        gate layers or all layers, respectively. The returned list then contains one instance of
        each distinct boxed layer (represented as a :class:`~.CircuitInstruction`) appearing
        in the input PUBs.

        Args:
            pubs: The list of PUBs to return a list of unique boxes for.
            types: The types of layers to return. Can be either ``"gates"`` or ``"all"``.

        Returns:
            The unique boxed layers found across the given PUBs.
        """
        coerced_pubs = [SamplerPub.coerce(pub, None) for pub in pubs]
        options = self.finalize_options()
        layers = find_unique_layers(
            pubs=coerced_pubs,
            twirling_options=options.twirling,
            measure_noise_learning=None,
            inject_noise=False,
            add_tags=True,
        )
        annotated_type = Tag if types == "all" else InjectNoise
        return [layer for layer in layers if get_annotation(layer, annotated_type)]

    def finalize_options(self) -> SamplerOptions:
        """Construct and finalize the Sampler options.

        This method produces the final :class:`~.SamplerOptions` instance used inside a call to
        :meth:`~.Sampler.run` by resolving the ``None`` in the twirling options as documented in
        :class:`~.TwirlingOptions`.

        Returns:
            The finalized :class:`~.SamplerOptions` object.
        """
        finalized_options = deepcopy(self.options)

        if finalized_options.twirling.enable_gates is None:
            finalized_options.twirling.enable_gates = False
        if finalized_options.twirling.enable_measure is None:
            finalized_options.twirling.enable_measure = False

        return finalized_options

    def run(self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None) -> RuntimeJobV2:
        """Submit a request to the sampler primitive.

        For moderate and complex workloads, the client-side processing done to map sampler inputs
        to executor inputs can be resource intensive and cause a delay
        between invoking the function and the ``job`` being submitted. In order to check the
        progress of the call, it is recommended to setup logging (with an ``INFO`` level) - see
        `IBM Quantum Compute documentation
        <https://quantum.cloud.ibm.com/docs/api/qiskit-ibm-runtime/runtime-service#logging>`_
        for more information.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                  or tuples ``(circuit, parameter_values)``.
            shots: The total number of shots to sample for each sampler pub that does
                   not specify its own shots. If ``None``, the value from
                   ``options.default_shots`` will be used.

        Returns:
            The submitted job.
        """
        # Coerce pubs to SamplerPub objects
        coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

        # Finalize the options--namely, resolve the ``None`` in the twirling options
        # as documented.
        options = self.finalize_options()

        # Determine default shots: run parameter takes precedence over options.default_shots
        default_shots = shots if shots is not None else options.default_shots

        # Legacy simulator path (no executor)
        if not (local_mode := self.options.experimental.get("local_mode", False)) and isinstance(
            self._service, QiskitRuntimeLocalService
        ):
            logger.info("Running in local simulator mode")

            options_dict = options.model_dump()
            options_dict["default_shots"] = shots

            return self._service._run(
                program_id="sampler",
                inputs={"pubs": coerced_pubs, "options": options_dict},
                options={"backend": self._backend},
                calibration_id=None,
            )

        # Convert pubs to QuantumProgram and map options using the prepare method
        logger.info("Starting pre-processing")
        quantum_program, executor_options = prepare(
            coerced_pubs, options, default_shots, add_tags=local_mode, backend=self._backend
        )
        # Store raw options for post-processing side to compute metadata.
        quantum_program.passthrough_data["post_processor"]["options"] = options.model_dump()  # type: ignore[index, call-overload]

        # Initialize executor with settings
        executor = Executor(mode=self._backend, options=executor_options)

        # Submit to executor
        logger.info(
            "Submitting %d pub%s to executor with %d shots",
            len(coerced_pubs),
            "s" if len(coerced_pubs) > 1 else "",
            quantum_program.shots,
        )

        return executor.run(quantum_program)
