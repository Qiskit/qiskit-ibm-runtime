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

"""Client-side Sampler primitive."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, get_args

from qiskit.primitives.base import BaseSamplerV2
from qiskit.primitives.containers.sampler_pub import SamplerPub

from ..base_client_side import BaseClientSide
from ..executor import Executor
from ..options_models.sampler import SamplerOptions
from .finalize_options import finalize_sampler_options
from .prepare import prepare
from .utils import BoxType, find_box_type, find_unique_layers

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction
    from qiskit.primitives.containers.sampler_pub import SamplerPubLike

    from ..fake_provider.local_runtime_job import LocalRuntimeJob
    from ..options_models import ExecutorOptions
    from ..quantum_program import QuantumProgram
    from ..runtime_job_v2 import RuntimeJobV2


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SamplerInputs:
    """The inputs of Sampler."""

    pubs: SamplerPubLike

    shots: int | None = None


class Sampler(BaseClientSide[SamplerInputs, SamplerOptions], BaseSamplerV2):
    """Client-side Sampler primitive for IBM Quantum Compute (formerly Qiskit Runtime).

    This is an implementation of Sampler built on top of the Executor primitive,
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
            from qiskit_ibm_runtime import Sampler

            service = QiskitRuntimeService()
            backend = service.least_busy(operational=True, simulator=False)

            # Create a simple circuit
            circuit = QuantumCircuit(2, 2)
            circuit.h(0)
            circuit.cx(0, 1)
            circuit.measure_all()

            # Run the sampler with options
            sampler = Sampler(mode=backend)
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
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`__
            for more information about execution modes.

        options: Sampler options. See :class:`~qiskit_ibm_runtime.options_models.SamplerOptions`
            for all available options.
    """

    def _get_default_options(self) -> SamplerOptions:
        """The default options of all :class:`~.Sampler` objects."""
        return SamplerOptions()

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
            The unique boxed layers of a certain type found across the given PUBs.
        """
        coerced_pubs = [SamplerPub.coerce(pub, None) for pub in pubs]
        options = self.finalize_options()
        layers = find_unique_layers(
            pubs=coerced_pubs,
            twirling_options=options.twirling,
            add_tags=True,
        )
        box_types = get_args(BoxType) if types == "all" else ("gates",)
        return [layer for layer in layers if find_box_type(layer) in box_types]

    def finalize_options(self) -> SamplerOptions:
        """Construct and finalize the Sampler options.

        This method produces the final :class:`~qiskit_ibm_runtime.options_models.SamplerOptions`
        instance used inside a call to :meth:`~.Sampler.run` by resolving the ``None`` in the
        twirling options as documented in
        :class:`~qiskit_ibm_runtime.options_models.TwirlingOptions`.

        Returns:
            The finalized :class:`~qiskit_ibm_runtime.options_models.SamplerOptions` object.
        """
        return finalize_sampler_options(self.options)

    def prepare(self, **kwargs: SamplerInputs) -> tuple[QuantumProgram, ExecutorOptions]:
        """The function used to map the inputs of Sampler to the inputs of Executor.

        Returns:
            A :class:`~.QuantumProgram` suitable for execution, along with the corresponding
                :class:`~.ExecutorOptions`.
        """
        return prepare(
            pubs=kwargs["pubs"],  # type: ignore[arg-type]
            options=self.options,
            shots=kwargs["shots"],  # type: ignore[arg-type]
            add_tags=self._service.is_local,
            backend=self._backend,
        )

    def run(
        self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None, dry_run: bool = False
    ) -> RuntimeJobV2 | LocalRuntimeJob:
        """Submit a request to the sampler primitive.

        For moderate and complex workloads, the client-side processing done to map sampler inputs
        to executor inputs can be resource intensive and cause a delay
        between invoking the function and the ``job`` being submitted. In order to check the
        progress of the call, it is recommended to setup logging (with an ``INFO`` level) - see
        :ref:`IBM Quantum Compute Logging information <logging_guide>` for more details.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                  or tuples ``(circuit, parameter_values)``.
            shots: The total number of shots to sample for each sampler pub that does
                   not specify its own shots. If ``None``, the value from
                   ``options.default_shots`` will be used.
            dry_run: If ``True``, performs a dry run without executing the job on a QPU. This mode
                can be used to validate the job, estimate usage consumption, and retrieve circuit
                timing metadata. Returned results preserve the expected schema but contain
                **randomized mock data** rather than actual or simulated measurement results.
                Unlike the fake backends, the processing of this dry run happens on the server-side,
                so the job may not finish immediately and access to this feature may be restricted.

        Returns:
            The submitted job.
        """
        # Pre-process: Convert Sampler input into a QuantumProgram
        logger.info("Starting pre-processing")
        quantum_program, executor_options = prepare(
            pubs,
            self.options,
            shots,
            add_tags=self._service.is_local,
            backend=self._backend,
        )

        # Set semantic role for post-processing dispatch
        quantum_program._semantic_role = "sampler_v2"

        executor = Executor(mode=self._mode or self._backend, options=executor_options)

        logger.info(
            "Submitting %d pub%s to executor with %d shots",
            len(quantum_program.items),
            "s" if len(quantum_program.items) > 1 else "",
            quantum_program.shots,
        )

        return executor.run(quantum_program, dry_run=dry_run)
