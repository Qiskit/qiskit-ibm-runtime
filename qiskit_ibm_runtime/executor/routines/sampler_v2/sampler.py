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

from collections.abc import Callable, Iterable
import logging
from typing import Any, Literal

from qiskit.primitives.base import BaseSamplerV2
from qiskit.primitives.containers.sampler_pub import SamplerPub, SamplerPubLike
from qiskit.providers import BackendV2
from qiskit.primitives import PrimitiveResult
from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic import build

from ....runtime_job_v2 import RuntimeJobV2
from ....executor import Executor
from ..dynamical_decoupling import generate_dd_pass_manager
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
    backend: BackendV2,
    default_shots: int | None = None,
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a list of :class:`~qiskit.primitives.containers.sampler_pub.SamplerPub`
    objects to a :class:`~.QuantumProgram` and map options.

    Args:
        pubs: List of sampler pubs to convert.
        options: :class:`~qiskit_ibm_runtime.executor.routines.options.sampler_options.SamplerOptions`
            to validate and map to
            :class:`~qiskit_ibm_runtime.options.executor_options.ExecutorOptions`.
        backend: Backend to use for dynamical decoupling timing information.
        default_shots: Default number of shots if not specified in pubs.

    Returns:
        A tuple containing:
        - :class:`~.QuantumProgram` with :class:`~.CircuitItem` objects for each pub,
            with passthrough_data configured for
            :class:`~qiskit_ibm_runtime.executor.routines.sampler_v2.SamplerV2` post-processing.
        - :class:`~qiskit_ibm_runtime.options.executor_options.ExecutorOptions` mapped from
            :class:`~qiskit_ibm_runtime.executor.routines.options.sampler_options.SamplerOptions`.

    Raises:
        IBMInputValueError: If circuits contain boxes or if shots are not specified.
        ValueError: If dynamical decoupling is enabled with dynamic circuits.
    """

    # Extract and validate shots from pubs
    shots = extract_shots_from_pubs(pubs, default_shots)

    twirling_enabled = options.twirling.enable_gates or options.twirling.enable_measure

    # Create DD pass manager if enabled
    dd_pass_manager = None
    if options.dynamical_decoupling.enable:
        # Validate that circuits don't have control flow (dynamic circuits)
        for pub in pubs:
            if pub.circuit.has_control_flow_op():
                raise ValueError(
                    "Dynamical decoupling is not compatible with dynamic circuits "
                    "(circuits with control flow operations)."
                )
        dd_pass_manager = generate_dd_pass_manager(
            backend=backend,
            options=options.dynamical_decoupling,
        )

    # Create items based on whether twirling is enabled
    items: list[QuantumProgramItem] = []
    program_shots = shots  # Default: use pub shots

    if not twirling_enabled:
        # No twirling path: validate no boxes, create CircuitItem objects
        for i, pub in enumerate(pubs):
            logger.info("Processing pub %d/%d", i, len(pubs))
            validate_no_boxes(pub.circuit)

            # Apply DD if enabled
            circuit = pub.circuit
            if dd_pass_manager is not None:
                circuit = dd_pass_manager.run(circuit)

            # Convert parameter values to numpy array
            if pub.parameter_values.num_parameters > 0:
                param_values = pub.parameter_values.as_array()
            else:
                param_values = None

            items.append(
                CircuitItem(
                    circuit=circuit,
                    circuit_arguments=param_values,
                )
            )
    else:
        # Twirling path: create SamplexItem objects
        num_rand, shots_per_rand = calculate_twirling_shots(
            shots,
            options.twirling.num_randomizations,
            options.twirling.shots_per_randomization,
        )

        program_shots = shots_per_rand

        boxing_pm = generate_boxing_pass_manager(
            enable_gates=bool(options.twirling.enable_gates),
            enable_measures=bool(options.twirling.enable_measure),
            twirling_strategy=options.twirling.strategy.replace("-", "_"),
        )

        for i, pub in enumerate(pubs):
            logger.info("Processing pub %d/%d", i, len(pubs))
            boxed_circuit = boxing_pm.run(pub.circuit)
            template_circuit, samplex = build(boxed_circuit)

            # Apply DD to template circuit if enabled
            if dd_pass_manager is not None:
                template_circuit = dd_pass_manager.run(template_circuit)

            # Prepare samplex_arguments
            if pub.parameter_values.num_parameters > 0:
                param_array = pub.parameter_values.as_array()
                samplex_args = {"parameter_values": param_array}
                # Shape should be (num_rand,) + parameter_sweep_shape
                param_shape = param_array.shape[:-1]  # Remove last dimension (num_parameters)
                item_shape = (num_rand,) + param_shape
            else:
                samplex_args = {}
                param_shape = ()
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

    passthrough_data = {
        "post_processor": {
            "context": "sampler_v2",
            "version": "v0.1",
            "twirling": options.twirling.enable_gates or options.twirling.enable_measure,
            "meas_type": options.execution.meas_type,
        }
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

    **Limitations:**

    - When twirling is disabled, circuits must not contain BoxOp instructions
    - Dynamical decoupling is incompatible with dynamic circuits.

    **Custom Prepare Function:**

    You can inject a custom prepare function to replace the default conversion logic
    from SamplerPub objects to QuantumProgram. The custom function must have the
    following signature:

    ```python

        def my_prepare(
            pubs: list[SamplerPub],
            options: SamplerOptions,
            backend: BackendV2,
            default_shots: int | None = None,
        ) -> tuple[QuantumProgram, ExecutorOptions]:
            ...
    ```

    The custom function can be provided either at initialization via the ``custom_prepare``
    parameter or later via the ``custom_prepare`` property. Set to ``None`` to restore
    the default prepare function.

    Example:
        .. code-block:: python

            from qiskit import QuantumCircuit
            from qiskit_ibm_runtime import QiskitRuntimeService
            from qiskit_ibm_runtime.executor.routines import SamplerV2

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

            # Example with custom prepare function
            def my_prepare(pubs, options, backend, default_shots=None):
                # Custom logic here
                ...
                return quantum_program, executor_options

            sampler = SamplerV2(mode=backend, custom_prepare=my_prepare)
            # Or set it later:
            # sampler.custom_prepare = my_prepare

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`~qiskit.providers.BackendV2` if you are using job mode.
            * A :class:`~qiskit_ibm_runtime.Session` if you are using session execution mode.
            * A :class:`~qiskit_ibm_runtime.Batch` if you are using batch execution mode.

            Refer to the `Qiskit Runtime documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
            for more information about execution modes.

        options: Sampler options.
            See :class:`~qiskit_ibm_runtime.executor.routines.options.sampler_options.SamplerOptions`
            for all available options.
        custom_prepare: Optional custom prepare function to replace the default conversion
            logic.
    """

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: SamplerOptions | dict | None = None,
        custom_prepare: (
            Callable[
                [list[SamplerPub], SamplerOptions, BackendV2, int | None],
                tuple[QuantumProgram, ExecutorOptions],
            ]
            | None
        ) = None,
    ):
        """Initialize the SamplerV2 primitive.

        Args:
            mode: The execution mode (:class:`~qiskit.providers.BackendV2`,
                :class:`~.Session`, or :class:`~.Batch`).
            options: Options for the sampler. Can be a
                :class:`~qiskit_ibm_runtime.executor.routines.options.sampler_options.SamplerOptions`
                instance or a dict.
            custom_prepare: Optional custom prepare function. Pass None to use the default.
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

        # Initialize prepare function
        self._prepare = custom_prepare if custom_prepare is not None else prepare

    def run(self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None) -> RuntimeJobV2:
        """Submit a request to the sampler primitive.

        For moderate and complex workloads, the client-side processing can be resource intensive
        and cause a delay between invoking the function and the ``job`` being submitted. In order
        to check the progress of the call, it is recommended to setup logging (with an ``INFO``
        level) - see `Qiskit Runtime documentation
        <https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/runtime-service#logging>`_
        for more information.

        Args:
            pubs: An iterable of pub-like objects. For example, a list of circuits
                  or tuples ``(circuit, parameter_values)``.
            shots: The total number of shots to sample for each sampler pub that does
                   not specify its own shots. If ``None``, the value from
                   ``options.default_shots`` will be used.

        Returns:
            The submitted job.

        Raises:
            ValueError: If backend is not provided.
            IBMInputValueError: If circuits contain :class:`~qiskit.circuit.BoxOp` instructions or if
                               shots are not properly specified.
            NotImplementedError: If unsupported options are enabled.
        """
        # Coerce pubs to SamplerPub objects
        coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

        # Determine default shots: run parameter takes precedence over options.default_shots
        default_shots = shots if shots is not None else self._options.default_shots

        # Get backend from executor
        backend = self._executor._backend
        if backend is None:
            raise ValueError(
                "Backend is required for SamplerV2. "
                "Please provide a backend when initializing the sampler."
            )

        # Convert pubs to QuantumProgram and map options using the prepare function
        logger.info("Starting pre-processing")
        quantum_program, executor_options = self._prepare(
            coerced_pubs, self._options, backend, default_shots
        )

        # Set executor options
        self._executor.options = executor_options

        # Submit to executor
        logger.info(
            "Submitting %d pub%s to executor with %d shots",
            len(coerced_pubs),
            "s" if len(coerced_pubs) > 1 else "",
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

    @property
    def custom_prepare(
        self,
    ) -> Callable[
        [list[SamplerPub], SamplerOptions, BackendV2, int | None],
        tuple[QuantumProgram, ExecutorOptions],
    ]:
        """Return the prepare function.

        Returns:
            The currently active prepare function.
        """
        return self._prepare

    @custom_prepare.setter
    def custom_prepare(
        self,
        fn: (
            Callable[
                [list[SamplerPub], SamplerOptions, BackendV2, int | None],
                tuple[QuantumProgram, ExecutorOptions],
            ]
            | None
        ),
    ) -> None:
        """Set the prepare function.

        Args:
            fn: The prepare function to use. Pass None to restore the default prepare function.

        Raises:
            TypeError: If fn is not None and not callable.
        """
        if fn is not None and not callable(fn):
            raise TypeError(f"custom_prepare must be callable or None, got {type(fn).__name__}")
        self._prepare = fn if fn is not None else prepare

    @staticmethod
    def quantum_program_result_to_primitive_result(
        result: QuantumProgramResult,
        metadata: dict[str, Any] | None = None,
        meas_type: Literal["classified", "kerneled"] = "classified",
    ) -> PrimitiveResult:
        """Convert :class:`~.QuantumProgramResult` to :class:`~qiskit.primitives.PrimitiveResult`.

        Args:
            result: The (possibly post-processed) quantum program result.
            metadata: The metadata to attach to the result.
            meas_type: How to process and return measurement results. This option sets the return
                type of all classical registers in all sampler pub results.

            * ``"classified"``: Returns a BitArray with classified measurement outcomes.
            * ``"kerneled"``: Returns complex IQ data points from kerneling the measurement
              trace, in arbitrary units.

        Returns:
            The converted primitive result.

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

            arrays = {}
            for creg_name, meas_data in item_data.items():
                if meas_type == "classified":
                    array = BitArray.from_bool_array(meas_data)
                elif meas_type == "kerneled":
                    array = meas_data
                arrays[creg_name] = array

            data_bin = DataBin(**arrays, shape=pub_shape)

            pub_result = SamplerPubResult(data=data_bin, metadata={})
            pub_results.append(pub_result)

        return PrimitiveResult(pub_results, metadata=metadata or {})
