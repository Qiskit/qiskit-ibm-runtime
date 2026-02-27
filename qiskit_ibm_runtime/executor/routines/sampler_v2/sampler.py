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
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic import build

from ....runtime_job_v2 import RuntimeJobV2
from ....executor import Executor
from ....session import Session
from ....batch import Batch
from ....quantum_program import QuantumProgram, QuantumProgramResult, QuantumProgramItem
from ....quantum_program.quantum_program import CircuitItem, SamplexItem
from ....options.executor_options import ExecutorOptions
from ..utils import validate_no_boxes, extract_shots_from_pubs, calculate_twirling_shots
from ..options.sampler_options import SamplerOptions

logger = logging.getLogger(__name__)


def prepare(
    pubs: list[SamplerPub],
    options: SamplerOptions,
    default_shots: int | None = None,
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a list of SamplerPub objects to a QuantumProgram and map options.

    Args:
        pubs: List of sampler pubs to convert.
        options: SamplerOptions to validate and map to ExecutorOptions.
        default_shots: Default number of shots if not specified in pubs.

    Returns:
        A tuple containing:
        - QuantumProgram with CircuitItem objects for each pub,
            with passthrough_data configured for SamplerV2 post-processing
        - ExecutorOptions mapped from SamplerOptions

    Raises:
        IBMInputValueError: If circuits contain boxes or if shots are not specified.
        NotImplementedError: If unsupported options are enabled.
    """

    # Validate options
    if options.dynamical_decoupling.enable:
        raise NotImplementedError(
            "Dynamical decoupling is not yet supported in the executor-based SamplerV2."
        )


    # Extract and validate shots from pubs
    shots = extract_shots_from_pubs(pubs, default_shots)

    twirling_options = options.twirling
    # Check if twirling is enabled
    twirling_enabled = twirling_options is not None and (
        twirling_options.enable_gates or twirling_options.enable_measure
    )
    # Create items based on whether twirling is enabled
    items: list[QuantumProgramItem] = []
    program_shots = shots  # Default: use pub shots

    if not twirling_enabled:
        # No twirling path: validate no boxes, create CircuitItem objects
        for pub in pubs:
            validate_no_boxes(pub.circuit)

            # Convert parameter values to numpy array
            if pub.parameter_values.num_parameters > 0:
                param_values = pub.parameter_values.as_array()
            else:
                param_values = None

            items.append(
                CircuitItem(
                    circuit=pub.circuit,
                    circuit_arguments=param_values,
                )
            )
    else:
        # Twirling path: create SamplexItem objects

        # Calculate twirling shots parameters
        num_rand, shots_per_rand = calculate_twirling_shots(
            shots,
            twirling_options.num_randomizations,
            twirling_options.shots_per_randomization,
        )

        # QuantumProgram.shots should be shots_per_randomization
        program_shots = shots_per_rand

        # Create boxing pass manager with twirling options
        boxing_pm = generate_boxing_pass_manager(
            enable_gates=bool(twirling_options.enable_gates),
            enable_measures=bool(twirling_options.enable_measure),
            twirling_strategy=twirling_options.strategy.replace("-", "_"),
        )

        for pub in pubs:
            boxed_circuit = boxing_pm.run(pub.circuit)
            template_circuit, samplex = build(boxed_circuit)

            # Prepare samplex_arguments
            if pub.parameter_values.num_parameters > 0:
                param_array = pub.parameter_values.as_array()
                samplex_args = {"parameter_values": param_array}
                # Shape should be (num_rand,) + parameter_sweep_shape
                param_shape = param_array.shape[:-1]  # Remove last dimension (num_parameters)
                item_shape = (num_rand,) + param_shape
            else:
                samplex_args = {}
                item_shape = (num_rand,)

            # Create SamplexItem
            items.append(
                SamplexItem(
                    circuit=template_circuit,
                    samplex=samplex,
                    samplex_arguments=samplex_args,
                    shape=item_shape,
                )
            )

    # Prepare passthrough_data with post-processor info
    passthrough_data = {
        "post_processor": {
            "context": "sampler_v2",
            "version": "v1",
        },
    }

    # Create QuantumProgram
    quantum_program = QuantumProgram(
        shots=program_shots,
        items=items,
        passthrough_data=passthrough_data,
        meas_level=options.execution.meas_type,
    )

    # Map options to executor options
    executor_options = options.to_executor_options()

    return quantum_program, executor_options


class SamplerV2(BaseSamplerV2):
    """Executor-based Sampler primitive for Qiskit Runtime.

    This is an implementation of SamplerV2 built on top of the Executor primitive,
    enabling transparent client-side processing with faster feedback loops and greater
    user control.

    **Supported Options:**

    - ``default_shots``: Default number of shots (default: 4096)
    - ``execution.init_qubits``: Whether to reset qubits (maps to executor)
    - ``execution.rep_delay``: Repetition delay (maps to executor)
    - ``twirling.*``: Twirling options (see :class:`TwirlingOptions`)
    - ``environment.*``: Environment options (log_level, job_tags, private)
    - ``max_execution_time``: Maximum execution time
    - ``experimental``: Experimental options (including image)

    **Unsupported Options (will raise NotImplementedError):**

    - ``dynamical_decoupling``: Dynamical decoupling sequences

    **Other Limitations:**

    - When twirling is disabled, circuits must not contain BoxOp instructions

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
        # Coerce pubs to SamplerPub objects
        coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

        # Determine default shots: run parameter takes precedence over options.default_shots
        default_shots = shots if shots is not None else self._options.default_shots

        # Convert pubs to QuantumProgram and map options
        quantum_program, executor_options = prepare(
            coerced_pubs, options=self._options, default_shots=default_shots
        )

        # Set executor options
        self._executor.options = executor_options

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

            bit_arrays = {}
            for creg_name, meas_data in item_data.items():
                bit_array = BitArray.from_bool_array(meas_data)
                bit_arrays[creg_name] = bit_array

            data_bin = DataBin(**bit_arrays, shape=pub_shape)

            pub_result = SamplerPubResult(data=data_bin, metadata={})
            pub_results.append(pub_result)

        return PrimitiveResult(pub_results, metadata={"quantum_program_metadata": result.metadata})
