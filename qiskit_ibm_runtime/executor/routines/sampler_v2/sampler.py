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
from typing import Literal

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
from ....options.executor_options import ExecutorOptions
from ....options.utils import Unset

from ..utils import validate_no_boxes, extract_shots_from_pubs
from .options import SamplerOptions

logger = logging.getLogger(__name__)


def prepare(
    pubs: list[SamplerPub],
    default_shots: int | None = None,
    meas_level: Literal["classified", "kerneled", "avg_kerneled"] | None = None,
) -> QuantumProgram:
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

    return QuantumProgram(
        shots=shots, items=items, passthrough_data=passthrough_data, meas_level=meas_level
    )


class SamplerV2(BaseSamplerV2):
    """Executor-based Sampler primitive for Qiskit Runtime.

    This is a new implementation of SamplerV2 built on top of the Executor primitive,
    enabling transparent client-side processing with faster feedback loops and greater
    user control.

    **Supported Options:**

    - ``default_shots``: Default number of shots (default: 4096)
    - ``execution.init_qubits``: Whether to reset qubits (maps to executor)
    - ``execution.rep_delay``: Repetition delay (maps to executor)
    - ``environment.*``: Environment options (log_level, job_tags, private)
    - ``max_execution_time``: Maximum execution time
    - ``experimental.image``: Runtime image

    **Unsupported Options (will raise NotImplementedError):**

    - ``dynamical_decoupling``: Dynamical decoupling sequences
    - ``twirling``: Pauli twirling
    - ``simulator.*``: Simulator options
    - ``experimental.*``: Other experimental options

    **Other Limitations:**

    - Circuits must not contain BoxOp instructions

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

            # Run the sampler with options
            sampler = SamplerV2(mode=backend)
            sampler.options.default_shots = 2048
            sampler.options.execution.init_qubits = True
            job = sampler.run([circuit])
            result = job.result()

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`Backend` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.

            Refer to the `Qiskit Runtime documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
            for more information about execution modes.

        options: Sampler options. See :class:`SamplerOptions` for all available options.
    """

    version = 2

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: SamplerOptions | dict | None = None,
    ):
        """Initialize the SamplerV2 primitive.

        Args:
            mode: The execution mode (Backend, Session, or Batch).
            options: Options for the sampler. Can be a SamplerOptions instance or a dict.
        """
        BaseSamplerV2.__init__(self)

        self._executor = Executor(mode=mode)

        # Initialize options
        if options is None:
            self._options = SamplerOptions()
        elif isinstance(options, dict):
            self._options = SamplerOptions(**options)
        else:
            self._options = options

    def run(self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None) -> RuntimeJobV2:
        """Submit a request to the sampler primitive.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                  or tuples ``(circuit, parameter_values)``.
            shots: The total number of shots to sample for each sampler pub that does
                   not specify its own shots. If ``None``, the value from
                   ``options.default_shots`` will be used.

        Returns:
            The submitted job.

        Raises:
            IBMInputValueError: If circuits contain BoxOp instructions or if
                               shots are not properly specified.
            NotImplementedError: If unsupported options are enabled.
        """
        # Map options to executor before running
        self._map_options_to_executor()

        # Coerce pubs to SamplerPub objects
        coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

        # Determine default shots: run parameter takes precedence over options.default_shots
        default_shots = shots if shots is not None else self._options.default_shots

        # Convert pubs to QuantumProgram
        meas_level = (
            self._options.execution.meas_type
            if self._options.execution.meas_type is not Unset
            else None
        )
        quantum_program = prepare(coerced_pubs, default_shots=default_shots, meas_level=meas_level)

        # Submit to executor
        logger.info(
            "Submitting %d pub(s) to executor with %d shots",
            len(coerced_pubs),
            quantum_program.shots,
        )

        return self._executor.run(quantum_program)

    @property
    def options(self) -> SamplerOptions:
        """Return the options.

        Returns:
            The sampler options.
        """
        return self._options

    def _map_options_to_executor(self) -> None:
        """Map SamplerV2 options to Executor options.

        This method maps the supported options from SamplerOptions to ExecutorOptions.
        For options that don't have a one-to-one correspondence or are not yet supported,
        it raises NotImplementedError.

        Raises:
            NotImplementedError: If unsupported options are enabled.
        """
        # Check for unsupported options and raise errors

        # Dynamical decoupling - not supported yet
        if self._options.dynamical_decoupling.enable:
            raise NotImplementedError(
                "Dynamical decoupling is not yet supported in the executor-based SamplerV2."
            )

        # Twirling - not supported yet
        if self._options.twirling.enable_gates or self._options.twirling.enable_measure:
            raise NotImplementedError(
                "Twirling is not yet supported in the executor-based SamplerV2."
            )

        # Experimental options (except 'image') - not supported yet
        if self._options.experimental is not None:
            if any(k != "image" for k in self._options.experimental.keys()):
                raise NotImplementedError(
                    "Experimental options (except image) are not supported in the "
                    "executor-based SamplerV2."
                )

        # Map supported options to executor options
        executor_options = ExecutorOptions()

        # Map execution options
        if (init_qubits := self._options.execution.init_qubits) is not Unset:
            executor_options.execution.init_qubits = init_qubits

        if (rep_delay := self._options.execution.rep_delay) is not Unset:
            executor_options.execution.rep_delay = rep_delay

        # Map environment options
        executor_options.environment.log_level = self._options.environment.log_level

        if (job_tags := self._options.environment.job_tags) is not None:
            executor_options.environment.job_tags = job_tags

        if (private := self._options.environment.private) is not None:
            executor_options.environment.private = private

        # Map max_execution_time
        if (max_exec_time := self._options.max_execution_time) is not None:
            executor_options.environment.max_execution_time = max_exec_time

        # Map experimental.image if present
        if self._options.experimental is not None and "image" in self._options.experimental:
            executor_options.environment.image = self._options.experimental["image"]

        # Update the executor's options
        self._executor.options = executor_options

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
