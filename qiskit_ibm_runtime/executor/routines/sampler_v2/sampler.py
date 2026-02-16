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
from qiskit.primitives import PrimitiveResult
from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult

from ....runtime_job_v2 import RuntimeJobV2
from ....executor import Executor
from ....session import Session
from ....batch import Batch
from ....quantum_program import QuantumProgram, QuantumProgramResult
from ....quantum_program.quantum_program import CircuitItem

from ..utils import validate_no_boxes, extract_shots_from_pubs

logger = logging.getLogger(__name__)


def prepare(pubs: list[SamplerPub], default_shots: int | None = None) -> QuantumProgram:
    """Convert a list of SamplerPub objects to a QuantumProgram.

    Args:
        pubs: List of sampler pubs to convert.
        default_shots: Default number of shots if not specified in pubs.

    Returns:
        A QuantumProgram containing CircuitItem objects for each pub,
        with passthrough_data configured for SamplerV2 post-processing.

    Raises:
        IBMInputValueError: If circuits contain boxes or if shots are not specified.
    """
    # Extract and validate shots from pubs
    shots = extract_shots_from_pubs(pubs, default_shots)

    # Validate circuits don't contain boxes
    for pub in pubs:
        validate_no_boxes(pub.circuit)

    # Create QuantumProgram with CircuitItem for each pub
    items = []
    for pub in pubs:
        # Convert parameter values to numpy array
        if pub.parameter_values.num_parameters > 0:
            # Get the parameter values as a numpy array
            param_values = pub.parameter_values.as_array()
        else:
            param_values = None

        items.append(
            CircuitItem(
                circuit=pub.circuit,
                circuit_arguments=param_values,
            )
        )

    # Prepare passthrough_data with post-processor info
    passthrough_data = {
        "post_processor": {
            "context": "sampler_v2",
            "version": "v1",
        },
    }

    return QuantumProgram(shots=shots, items=items, passthrough_data=passthrough_data)


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

    def run(self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None) -> RuntimeJobV2:
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
        default_shots = (
            shots if shots is not None else 4096
        )  # TODO: Move to options once available.
        quantum_program = prepare(coerced_pubs, default_shots=default_shots)

        # Submit to executor
        logger.info(
            "Submitting %d pub(s) to executor with %d shots",
            len(coerced_pubs),
            quantum_program.shots,
        )

        return self._executor.run(quantum_program)

    @property
    def options(self) -> None:
        """Return the options.

        Note:
            Options are not yet supported in this minimal implementation.
            This property is provided for interface compatibility.
        """
        # Return a minimal options object for compatibility
        # In future phases, this will return a proper SamplerOptions instance
        return None

    @staticmethod
    def quantum_program_result_to_primitive_result(result: QuantumProgramResult) -> PrimitiveResult:
        """Convert QuantumProgramResult to PrimitiveResult.

        Args:
            result: The (possibly post-processed) quantum program result.

        Returns:
            PrimitiveResult containing SamplerPubResult objects.

        Raises:
            ValueError: If data is malformed or inconsistent
        """
        # Build SamplerPubResult for each pub
        pub_results = []
        for idx, item_data in enumerate(result):
            # Validate that measurement data exists
            if not item_data:
                raise ValueError(f"Pub {idx} has no measurement data")

            # Infer pub_shape from the first classical register's data
            # meas_data shape: (...pub_shape..., num_shots, num_bits)
            first_meas_data = next(iter(item_data.values()))
            pub_shape = first_meas_data.shape[:-2]

            # Create BitArray for each classical register found in the data
            bit_arrays = {}
            for creg_name, meas_data in item_data.items():
                # Create BitArray from measurement data (bit array format)
                # meas_data shape: (..., num_shots, num_clbits)
                bit_array = BitArray.from_bool_array(meas_data)
                bit_arrays[creg_name] = bit_array

            data_bin = DataBin(**bit_arrays, shape=pub_shape)

            pub_result = SamplerPubResult(data=data_bin, metadata={})
            pub_results.append(pub_result)

        # Create and return PrimitiveResult with preserved metadata
        return PrimitiveResult(pub_results, metadata={"quantum_program_metadata": result.metadata})
