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
from typing import TYPE_CHECKING

from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from ..executor.calculate_twirling_shots import calculate_twirling_shots
from ..quantum_program import QuantumProgram
from ..quantum_program.quantum_program import CircuitItem, SamplexItem
from .utils import (
    extract_shots_from_pubs,
    validate_meas_type_twirling,
    validate_no_boxes,
    validate_twirling_option_fileds_are_not_none,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.sampler_pub import SamplerPub

    from ..options_models.executor_options import ExecutorOptions
    from ..options_models.sampler_options import SamplerOptions
    from ..quantum_program import QuantumProgramItem


logger = logging.getLogger(__name__)


def prepare(
    pubs: Sequence[SamplerPub], options: SamplerOptions, default_shots: int | None = None
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a sequence of sampler PUBs to a quantum program and map options.

    This method processes sampler PUBs (Primitive Unified Blocs) and converts them into
    a :class:`~.QuantumProgram` suitable for execution, along with the corresponding
    :class:`~.ExecutorOptions`.

    Args:
        pubs: List of sampler PUBs to convert.
        options: The options.
        default_shots: Default number of shots if not specified in PUBs. If ``None``,
            uses the value from ``self.options.default_shots``.

    Returns:
        A tuple containing:

        - :class:`~.QuantumProgram` with :class:`~.CircuitItem` or :class:`~.SamplexItem`
            objects for each pub, with passthrough_data configured for post-processing.
        - :class:`~.ExecutorOptions` mapped from the sampler's options.

    Raises:
        ValueError: If backend is not provided or if dynamical decoupling is enabled
            with dynamic circuits.
        IBMInputValueError: If circuits contain :class:`~qiskit.circuit.BoxOp` instructions
            (when twirling is disabled), if shots are not properly specified, or if
            measurement twirling is enabled with a non-classified ``meas_type``.
    """
    validate_twirling_option_fileds_are_not_none(options.twirling)
    validate_meas_type_twirling(options.execution.meas_type, options.twirling.enable_measure)

    # Extract and validate shots from pubs
    shots = extract_shots_from_pubs(pubs, default_shots)

    twirling_enabled = options.twirling.enable_gates or options.twirling.enable_measure

    # Validate DD compatibility if enabled
    if options.dynamical_decoupling.enable:
        # Validate that circuits don't have control flow (dynamic circuits)
        for pub in pubs:
            if pub.circuit.has_control_flow_op():
                raise ValueError(
                    "Dynamical decoupling is not compatible with dynamic circuits "
                    "(circuits with control flow operations)."
                )

    # Create items based on whether twirling is enabled
    items: list[QuantumProgramItem] = []
    program_shots = shots  # Default: use pub shots

    if not twirling_enabled:
        # No twirling path: validate no boxes, create CircuitItem objects
        for i, pub in enumerate(pubs):
            logger.info("Processing pub %d/%d", i + 1, len(pubs))
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
            inject_noise_site="after",
        )

        for i, pub in enumerate(pubs):
            logger.info("Processing pub %d/%d", i + 1, len(pubs))
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
            "twirling": options.twirling.enable_gates or options.twirling.enable_measure,
            "meas_type": options.execution.meas_type,
            "shots": program_shots,
            "circuits_metadata": [pub.circuit.metadata for pub in pubs],
        }
    }

    # Create QuantumProgram
    quantum_program = QuantumProgram(
        shots=program_shots,
        items=items,
        passthrough_data=passthrough_data,
        meas_level=options.execution.meas_type,
    )
    quantum_program._semantic_role = "sampler_v2"

    # Map options to executor options
    executor_options = options.to_executor_options()

    return quantum_program, executor_options
