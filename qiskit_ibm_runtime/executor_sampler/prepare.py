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

"""Prepare function for Executor-based SamplerV2 primitive."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qiskit.primitives.containers.sampler_pub import SamplerPub
from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from ..exceptions import IBMInputValueError
from ..executor.calculate_twirling_shots import calculate_twirling_shots
from ..executor.dynamical_decoupling import apply_dynamical_decoupling
from ..options_models.converters import sampler_option_to_executor_options
from ..quantum_program import QuantumProgram
from ..quantum_program.quantum_program import CircuitItem, SamplexItem
from ..utils.utils import validate_no_boxes
from .finalize_options import finalize_sampler_options
from .utils import (
    extract_shots_from_pubs,
    validate_meas_type_twirling,
    validate_twirling_option_fields_are_not_none,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from qiskit.primitives.containers.sampler_pub import SamplerPubLike
    from qiskit.providers import BackendV2

    from ..options_models.executor import ExecutorOptions
    from ..options_models.sampler import SamplerOptions
    from ..quantum_program import QuantumProgramItem


logger = logging.getLogger(__name__)


def prepare(
    pubs: Iterable[SamplerPubLike],
    options: SamplerOptions,
    shots: int | None = None,
    add_tags: bool = False,
    backend: BackendV2 | None = None,
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a sequence of sampler PUBs to a quantum program and map options.

    This method processes sampler PUBs (Primitive Unified Blocs) and converts them into
    a :class:`~.QuantumProgram` suitable for execution, along with the corresponding
    :class:`~.ExecutorOptions`.

    Args:
        pubs: Iterable of PUB-like objects to convert.
        options: The sampler options.
        shots: The total number of shots to sample for each sampler pub that does not specify its
            own shots. If ``None``, the value from ``options.default_shots`` will be used.
        add_tags: Whether to include tags for the boxes. ``False`` will cause no tags to be added
            (will pass the ``"none"`` value to the relevant attribute), while ``True`` will cause
            tags with the twirled boxes hash to be added (using the ``"unique_box"`` value of the
            relevant attribute). These tags are used to inject noise when running in local mode.
        backend: The backend for which the program is prepared. Only required when dynamical
            decoupling is enabled.

    Returns:
        A tuple containing:

        - :class:`~.QuantumProgram` with :class:`~.CircuitItem` or :class:`~.SamplexItem`
            objects for each pub, with passthrough_data configured for post-processing.
        - :class:`~.ExecutorOptions` The finalized sampler options.

    Raises:
        IBMInputValueError: If no pubs are provided, if circuits contain
            :class:`~qiskit.circuit.BoxOp` instructions (when twirling is disabled),
            if shots are not properly specified, if measurement twirling is enabled
            with a non-classified ``meas_type``, if dynamical decoupling is enabled
            with dynamic circuits, or if dynamical decoupling is enabled without a backend.
    """
    # Coerce PUBs
    coerced_pubs = [SamplerPub.coerce(pub, shots) for pub in pubs]

    # Finalize options (resolve None twirling fields)
    finalized_options = finalize_sampler_options(options)

    _validate(coerced_pubs, finalized_options, backend)

    executor_options = sampler_option_to_executor_options(finalized_options)

    # Resolve shots: run parameter takes precedence over options.default_shots
    default_shots = shots if shots is not None else finalized_options.default_shots
    resolved_shots = extract_shots_from_pubs(coerced_pubs, default_shots)

    quantum_program = _build_quantum_program(
        coerced_pubs, finalized_options, resolved_shots, add_tags, backend
    )

    # Annotate passthrough_data for post-processing
    quantum_program.passthrough_data["post_processor"]["options"] = finalized_options.model_dump()  # type: ignore[index, call-overload]

    return quantum_program, executor_options


def _validate(
    coerced_pubs: Sequence[SamplerPub],
    finalized_options: SamplerOptions,
    backend: BackendV2 | None,
) -> None:
    """Validate the coerced pubs and finalized options.

    Args:
        coerced_pubs: The coerced sampler pubs.
        finalized_options: The finalized sampler options.
        backend: The backend for which the program is prepared.

    Raises:
        IBMInputValueError: If no pubs are provided, if circuits contain
            :class:`~qiskit.circuit.BoxOp` instructions (when twirling is disabled),
            if measurement twirling is enabled with a non-classified ``meas_type``,
            if dynamical decoupling is enabled with dynamic circuits, or if dynamical
            decoupling is enabled without a backend.
    """
    if not coerced_pubs:
        raise IBMInputValueError("No pubs provided. At least one pub is required.")

    validate_twirling_option_fields_are_not_none(finalized_options.twirling)
    validate_meas_type_twirling(
        finalized_options.execution.meas_type, finalized_options.twirling.enable_measure
    )

    for pub in coerced_pubs:
        validate_no_boxes(pub.circuit)

        if finalized_options.dynamical_decoupling.enable:
            if pub.circuit.has_control_flow_op():
                raise IBMInputValueError(
                    "Dynamical decoupling is not compatible with dynamic circuits "
                    "(circuits with control flow operations)."
                )
            if backend is None:
                raise IBMInputValueError(
                    "A backend must be provided when dynamical decoupling is enabled."
                )


def _build_quantum_program(
    coerced_pubs: Sequence[SamplerPub],
    finalized_options: SamplerOptions,
    resolved_shots: int,
    add_tags: bool,
    backend: BackendV2 | None,
) -> QuantumProgram:
    """Build the quantum program, applying twirling and dynamical decoupling.

    Args:
        coerced_pubs: The coerced sampler pubs.
        finalized_options: The finalized sampler options.
        resolved_shots: The number of shots resolved from the pubs and options.
        add_tags: Whether to include tags for the boxes.
        backend: The backend for which the program is prepared.

    Returns:
        The prepared quantum program.
    """
    program_shots = resolved_shots

    items: list[QuantumProgramItem] = []
    if not (finalized_options.twirling.enable_gates or finalized_options.twirling.enable_measure):
        # No twirling path: create CircuitItem objects
        for i, pub in enumerate(coerced_pubs):
            logger.info("Processing pub %d/%d", i + 1, len(coerced_pubs))
            # Convert parameter values to numpy array. Pass the circuit's
            # parameters so the columns are ordered to match ``circuit.parameters``.
            if pub.parameter_values.num_parameters > 0:
                param_values = pub.parameter_values.as_array(pub.circuit.parameters)
            else:
                param_values = None

            circuit = pub.circuit
            if circuit.metadata:
                circuit = circuit.copy()  # copy the circuit to avoid mutating the original
                circuit.metadata = {}  # clear the metadata as it is now passthrough data
            items.append(
                CircuitItem(
                    circuit=circuit,
                    circuit_arguments=param_values,
                )
            )
    else:
        # Twirling path: create SamplexItem objects
        num_rand, shots_per_rand = calculate_twirling_shots(
            resolved_shots,
            finalized_options.twirling.num_randomizations,
            finalized_options.twirling.shots_per_randomization,
        )

        program_shots = shots_per_rand

        boxing_pm = generate_boxing_pass_manager(
            enable_gates=bool(finalized_options.twirling.enable_gates),
            enable_measures=bool(finalized_options.twirling.enable_measure),
            twirling_strategy=finalized_options.twirling.strategy.replace("-", "_"),
            inject_noise_site="after",
            add_tags="unique_box" if add_tags else "none",
            twirling_group=finalized_options.twirling.group,
        )

        for i, pub in enumerate(coerced_pubs):
            logger.info("Processing pub %d/%d", i + 1, len(coerced_pubs))
            boxed_circuit = boxing_pm.run(pub.circuit)
            template_circuit, samplex = build(boxed_circuit)

            # Prepare samplex_arguments
            if pub.parameter_values.num_parameters > 0:
                param_array = pub.parameter_values.as_array(pub.circuit.parameters)
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
            "version": "v0.1",
            "twirling": finalized_options.twirling.enable_gates
            or finalized_options.twirling.enable_measure,
            "meas_type": finalized_options.execution.meas_type,
            "shots": program_shots,
            "circuits_metadata": [pub.circuit.metadata for pub in coerced_pubs],
        }
    }

    quantum_program = QuantumProgram(
        shots=program_shots,
        items=items,
        passthrough_data=passthrough_data,
        meas_level=finalized_options.execution.meas_type,
    )

    if finalized_options.dynamical_decoupling.enable:
        logger.info("Apply dynamical decoupling")
        quantum_program = apply_dynamical_decoupling(
            backend=backend,
            dd_options=finalized_options.dynamical_decoupling,
            quantum_program=quantum_program,
        )

    return quantum_program
