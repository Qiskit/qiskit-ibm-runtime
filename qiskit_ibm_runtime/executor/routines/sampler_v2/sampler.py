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

from collections.abc import Iterable
import logging

from qiskit.primitives.base import BaseSamplerV2
from qiskit.primitives.containers.sampler_pub import SamplerPub, SamplerPubLike
from qiskit.providers import BackendV2

from ....runtime_job_v2 import RuntimeJobV2
from ....executor import Executor
from ....session import Session
from ....batch import Batch

from ..utils import pubs_to_quantum_program

logger = logging.getLogger(__name__)


class SamplerV2(BaseSamplerV2):
    """Executor-based Sampler primitive for Qiskit Runtime.

    This is a new implementation of SamplerV2 built on top of the Executor primitive,
    enabling transparent client-side processing with faster feedback loops and greater
    user control.

    **Current Limitations (Minimal Implementation):**

    - No options support (twirling, dynamical decoupling, etc.)
    - Circuits must not contain BoxOp instructions
    - Uses default shots if not specified in pubs

    These limitations will be addressed in future phases of development.

    Example:
        .. code-block:: python

            from qiskit import QuantumCircuit
            from qiskit_ibm_runtime import QiskitRuntimeService
            from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerV2

            service = QiskitRuntimeService()
            backend = service.least_busy(operational=True, simulator=False)

            # Create a simple circuit
            circuit = QuantumCircuit(2, 2)
            circuit.h(0)
            circuit.cx(0, 1)
            circuit.measure_all()

            # Run the sampler
            sampler = SamplerV2(mode=backend)
            job = sampler.run([circuit], shots=1024)
            result = job.result()

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`Backend` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.

            Refer to the `Qiskit Runtime documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
            for more information about execution modes.
    """

    version = 2

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
    ):
        """Initialize the SamplerV2 primitive.

        Args:
            mode: The execution mode (Backend, Session, or Batch).
        """
        BaseSamplerV2.__init__(self)
        
        self._executor = Executor(mode=mode)
        
    def run(
        self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None
    ) -> RuntimeJobV2:
        """Submit a request to the sampler primitive.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                  or tuples ``(circuit, parameter_values)``.
            shots: The total number of shots to sample for each sampler pub that does
                   not specify its own shots. If ``None``, a default value will be used.

        Returns:
            The submitted job.

        Raises:
            IBMInputValueError: If circuits contain BoxOp instructions or if
                               shots are not properly specified.
        """
        # Coerce pubs to SamplerPub objects
        coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

        # Convert pubs to QuantumProgram
        default_shots = shots if shots is not None else 4096 # TODO: Move to options once available. 
        quantum_program = pubs_to_quantum_program(coerced_pubs, default_shots=default_shots)

        # Submit to executor
        logger.info(
            "Submitting %d pub(s) to executor with %d shots",
            len(coerced_pubs),
            quantum_program.shots,
        )
        
        return self._executor.run(quantum_program)

    @property
    def options(self):
        """Return the options.

        Note:
            Options are not yet supported in this minimal implementation.
            This property is provided for interface compatibility.
        """
        # Return a minimal options object for compatibility
        # In future phases, this will return a proper SamplerOptions instance
        return None