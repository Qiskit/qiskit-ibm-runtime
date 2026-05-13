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

"""Prepare function for Executor-based EstimatorV2 primitive."""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from ..options_models.twirling_options import TwirlingOptions

import numpy as np
from samplomatic import build, ChangeBasis
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import replace_annotations, get_annotation
from qiskit.circuit import ClassicalRegister
from qiskit.circuit.exceptions import CircuitError

from ..quantum_program import QuantumProgram
from ..quantum_program.quantum_program import SamplexItem
from ..quantum_program.datatree import is_datatree_compatible
from ..exceptions import IBMInputValueError
from .utils import get_bases, pauli_to_ints
from ..executor.calculate_twirling_shots import calculate_twirling_shots

logger = logging.getLogger(__name__)


def prepare(
    pubs: Sequence[EstimatorPub], twirling_options: TwirlingOptions, shots: int
) -> QuantumProgram:
    """Convert estimator PUBs to a quantum program.

    Args:
        pubs: List of estimator pubs to convert.
        twirling_options: The twirling options.
        shots: The number of shots to use. Will be overridden by
            ``num_randomizations * shots_per_randomization`` when both are specified explicitly
            and twirling is on.

    Returns:
        :class:`~.QuantumProgram` with :class:`~.SamplexItem` objects for each pub,
        with ``passthrough data`` configured for
        :class:`~qiskit_ibm_runtime.executor_estimator.estimator.EstimatorV2` post-processing.

    Raises:
        IBMInputValueError: If pubs have mismatched precision,
            if a circuit contains mid-circuit measurements, or if a circuit already uses the
            reserved classical register name ``_meas``.
    """
    if twirling_options.enable_gates or twirling_options.enable_measure:
        num_randomizations, shots_per_randomization = calculate_twirling_shots(
            shots,
            twirling_options.num_randomizations,
            twirling_options.shots_per_randomization,
        )
    else:
        num_randomizations = 1
        shots_per_randomization = shots

    # Create items
    items: list[SamplexItem] = []
    observables_list = []
    measure_bases_list = []

    for i, pub in enumerate(pubs):
        logger.info("Processing pub %d/%d", i + 1, len(pubs))

        # Determine measurement bases
        measure_bases = get_bases(pub.observables)

        # Remove any existing final measurements
        prepared_circuit = pub.circuit.remove_final_measurements(inplace=False)

        # Add final measurements
        creg = ClassicalRegister(prepared_circuit.num_qubits, "_meas")
        try:
            prepared_circuit.add_register(creg)
        except CircuitError:
            raise IBMInputValueError("Name `_meas` is reserved for a dedicated classical register.")
        prepared_circuit.measure(prepared_circuit.qubits, creg)

        # Add boxes
        boxing_pm = generate_boxing_pass_manager(
            enable_gates=twirling_options.enable_gates,
            enable_measures=True,
            twirling_strategy=twirling_options.strategy.replace("-", "_"),
            measure_annotations="all" if twirling_options.enable_measure else "change_basis",
        )
        boxed_circuit = boxing_pm.run(prepared_circuit)

        # Remove change basis annotations from every box except the last one
        basis_changes_ref = get_annotation(boxed_circuit[-1].operation, ChangeBasis).ref
        boxed_circuit = replace_annotations(
            boxed_circuit,
            lambda a: [] if (isinstance(a, ChangeBasis) and a.ref != basis_changes_ref) else [a],
        )

        template, samplex = build(boxed_circuit)

        # Prepare samplex_arguments
        if pub.parameter_values.num_parameters > 0:
            param_array = pub.parameter_values.as_array()
            param_shape = pub.parameter_values.shape
            samplex_args = {
                "parameter_values": param_array.reshape(
                    param_shape + (1, pub.parameter_values.num_parameters)
                )
            }
        else:
            samplex_args = {}
            param_shape = ()

        item_shape = (num_randomizations,) + param_shape + (len(measure_bases),)

        samplex_arguments = samplex.inputs().make_broadcastable()
        samplex_arguments.bind(
            **{
                **samplex_args,
                "basis_changes": {
                    basis_changes_ref: np.array([pauli_to_ints(basis) for basis in measure_bases])
                },
            }
        )

        # Create SamplexItem
        items.append(
            SamplexItem(
                circuit=template,
                samplex=samplex,
                samplex_arguments=samplex_arguments,
                shape=item_shape,
            )
        )

        # Store data for passthrough
        observables_list.append(pub.observables.tolist())
        measure_bases_list.append(measure_bases.to_labels())

    # Collect circuit metadata from each pub
    circuits_metadata = [pub.circuit.metadata for pub in pubs]

    # Validate that circuit metadata is compatible with DataTree format
    for idx, metadata in enumerate(circuits_metadata):
        if metadata is not None and not is_datatree_compatible(metadata):
            raise IBMInputValueError(
                f"Circuit metadata at index {idx} is not compatible with DataTree format. "
                f"Metadata must be a nested structure of lists, dicts (with string keys), "
                f"numpy arrays, or primitive types (str, int, float, bool, None)."
            )

    passthrough_data = {
        "post_processor": {
            "version": "v0.1",
            "circuits_metadata": circuits_metadata,
            "observables": observables_list,
            "measure_bases": measure_bases_list,
        },
    }

    # Create QuantumProgram
    quantum_program = QuantumProgram(
        shots=shots_per_randomization,
        items=items,
        passthrough_data=passthrough_data,
    )

    # Set semantic role for post-processing dispatch
    quantum_program._semantic_role = "estimator_v2"

    return quantum_program
