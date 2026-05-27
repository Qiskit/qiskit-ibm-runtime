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
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy.typing as npt
    from qiskit.primitives.containers.estimator_pub import EstimatorPub

    from ..options_models.twirling_options import TwirlingOptions
    from ..options_models.measure_noise_learning_options import MeasureNoiseLearningOptions

import numpy as np
from qiskit.circuit import ClassicalRegister
from qiskit.circuit.exceptions import CircuitError
from qiskit.quantum_info import Pauli, PauliList
from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from ..exceptions import IBMInputValueError
from .trex_utils import create_trex_calibration_circuit
from ..executor.calculate_twirling_shots import calculate_twirling_shots
from ..quantum_program import QuantumProgram
from ..quantum_program.datatree import is_datatree_compatible
from ..quantum_program.quantum_program import SamplexItem
from .utils import get_pauli_basis, pauli_to_ints, unbroadcast_index

logger = logging.getLogger(__name__)


def prepare(
    pubs: Sequence[EstimatorPub],
    twirling_options: TwirlingOptions,
    shots: int,
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
) -> QuantumProgram:
    """Convert estimator PUBs to a quantum program.

    Args:
        pubs: List of estimator pubs to convert.
        twirling_options: The twirling options.
        shots: The number of shots to use. Will be overridden by
            ``num_randomizations * shots_per_randomization`` when both are specified explicitly
            and twirling is on.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be used.

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
    param_basis_pairs_list = []
    param_shapes_list = []

    for i, pub in enumerate(pubs):
        logger.info("Processing pub %d/%d", i + 1, len(pubs))

        # Remove any existing final measurements
        prepared_circuit = pub.circuit.remove_final_measurements(inplace=False)

        if prepared_circuit.get_instructions("measure"):
            raise IBMInputValueError(
                f"Pub {i} contains mid-circuit measurements, which are temporarily not supported"
                " by EstimatorV2. Only final measurements are allowed."
            )

        creg = ClassicalRegister(prepared_circuit.num_qubits, "_meas")
        try:
            prepared_circuit.add_register(creg)
        except CircuitError:
            raise IBMInputValueError("Name `_meas` is reserved for a dedicated classical register.")

        prepared_circuit.measure(prepared_circuit.qubits, creg)

        boxing_pm = generate_boxing_pass_manager(
            enable_gates=twirling_options.enable_gates,
            enable_measures=True,
            twirling_strategy=twirling_options.strategy.replace("-", "_"),
            measure_annotations="all"
            if twirling_options.enable_measure or measure_noise_learning is not None
            else "change_basis",
        )
        prepared_circuit = boxing_pm.run(prepared_circuit)

        # Build the template and the samplex
        template, samplex = build(prepared_circuit)

        # Get the name of the basis changing ref
        basis_changes_specs = samplex.inputs().get_specs("basis_changes")
        basis_changes_name = basis_changes_specs[0].name

        # Prepare samplex_arguments
        flat_parameter_values, change_basis, param_basis_pairs = compute_samplex_arguments(pub)
        samplex_arguments = {basis_changes_name: change_basis}
        if samplex.inputs().get_specs("parameter_values"):
            samplex_arguments["parameter_values"] = flat_parameter_values

        # Create SamplexItem
        shape = (num_randomizations, change_basis.shape[0])
        items.append(
            SamplexItem(
                circuit=template,
                samplex=samplex,
                samplex_arguments=samplex_arguments,
                shape=shape,
            )
        )

        # Store data for passthrough
        observables_list.append(pub.observables.tolist())
        param_basis_pairs_list.append(param_basis_pairs)
        param_shapes_list.append(pub.parameter_values.shape)

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
            "param_basis_pairs": param_basis_pairs_list,
            "param_shapes": param_shapes_list,
            "measure_mitigation": "False",
        },
    }

    # Create QuantumProgram
    quantum_program = QuantumProgram(
        shots=shots_per_randomization,
        items=items,
        passthrough_data=passthrough_data,
    )

    # Add TREX calibration circuit
    if measure_noise_learning is not None:
        if (
            isinstance(measure_noise_learning.shots_per_randomization, int)
            and measure_noise_learning.shots_per_randomization != shots_per_randomization
        ):
            raise IBMInputValueError(
                "shots_per_randomization must be the same for twirling and measure_noise_learning"
            )
        trex_item = create_trex_calibration_circuit(pubs, measure_noise_learning)
        quantum_program.items.append(trex_item)
        passthrough_data["post_processor"]["measure_mitigation"] = "True"

    # Set semantic role for post-processing dispatch
    quantum_program._semantic_role = "estimator_v2"

    return quantum_program


def compute_samplex_arguments(
    pub: EstimatorPub,
) -> tuple[npt.NDArray[float], npt.NDArray[int], list[tuple[tuple[int, ...], str]]]:
    """Compute parameter values and basis changes to be used as inputs by the samplex.

    To minimize the total number of circuits executions, this function takes the following
    steps:
        1. It creates a map between subsets of parameters and the observables that need to
           be measured for each subset, applying broadcasting rules to params and observables.
        2. It replaces the observables in that map with the minimal set of Pauli basis that
           can be used to measure all such observables.
        3. It flattens the map into two 1D arrays of equal lenght, containing the subsets of
           parameters and basis changing gates respectively. When a subset of parameter maps
           to more than one basis changing gate, the flattened array contains multiple copies
           of it.

    Overall, the two 1D arrays returned contain ``N`` elements, where ``N`` is the total number
    of basis changing gates that need to be measured across all the different parameter sets.
    Zipping them yields parameter–basis pairs, where each parameter value must be measured using
    its associated change basis.

    The two arrays have the format required by samplomatic and can be pass straight to the samplex
    via ``samplex.inputs()``.

    Args:
        pub: An estimator PUB.

    Return:
        A tuple ``(flat_parameter_values, change_basis, param_basis_pairs)`` where:

            * ``flat_parameter_values`` is a 1-D array of parameter values in the format expected
            by ``samplex.inputs()``. The array is of length ``N``, the total number of
            basis-changing gates required across all parameter sets.

            * ``change_basis`` is a 1-D array of length ``N`` containing the basis-changing gates
            associated with ``flat_parameter_values``, also in the format expected by
            ``samplex.inputs()``.

            * ``param_basis_pairs`` is a list of ``N`` tuples ``(ndindex, basis)`` describing the
            correspondence between the two arrays. For the i-th tuple:
                - ``ndindex`` is the N-dimensional index of the parameter entry in
                    ``pub.parameter_values``.
                - ``basis`` is the measurement basis associated with that parameter entry.
    """
    parameter_values = pub.parameter_values
    observables = pub.observables
    bcast_shape = pub.shape

    # Step 1.
    # Generate a map between param ndindices to pauli basis and the observable terms that they
    # measure
    param_obs_map: dict[set] = defaultdict(lambda: defaultdict(set))  # type: ignore[type-arg]
    for bcast_index in np.ndindex(bcast_shape):
        param_index = unbroadcast_index(bcast_index, parameter_values.shape)
        obs = observables[unbroadcast_index(bcast_index, observables.shape)]
        for obs_term, _ in obs.items():
            pauli_basis = get_pauli_basis(obs_term)
            param_obs_map[param_index][pauli_basis].add(obs_term)

    # Step 2.
    # Collect the Paulis to measure for each parameter value in commuting sets
    param_meas_groups_map = {}
    for param_index, pauli_map in param_obs_map.items():
        pauli_set = list(pauli_map)
        meas_groups = PauliList(pauli_set).group_commuting(qubit_wise=True)
        param_meas_groups_map[param_index] = meas_groups

    # Figure out measurement Pauli basis for each set of commuting Paulis
    param_basis_map = {}
    for param_index, meas_groups in param_meas_groups_map.items():
        param_basis_map[param_index] = [
            Pauli((np.logical_or.reduce(paulis.z), np.logical_or.reduce(paulis.x)))
            for paulis in meas_groups
        ]

    # Step 3. Flatten the params.
    # We flatten params into a 1D array and generate a corresponding 1D `change_basis` array. Both
    # arrays contain ``num_basis`` elements.
    num_basis = sum(len(basis) for basis in param_basis_map.values())
    flat_parameter_values = np.empty(
        (num_basis, parameter_values.num_parameters),
        dtype=float,
    )
    change_basis = np.empty((num_basis, observables.num_qubits), dtype=int)

    basis_idx = 0
    for ndindex, basis in param_basis_map.items():
        for bases in basis:
            change_basis[basis_idx] = pauli_to_ints(bases)
            flat_parameter_values[basis_idx] = parameter_values.as_array()[ndindex]
            basis_idx += 1

    # Step 4. Log info.
    param_basis_pairs: list[tuple[tuple[int, ...], str]] = [
        (ndindex, bases.to_label()) for ndindex, basis in param_basis_map.items() for bases in basis
    ]

    return flat_parameter_values, change_basis, param_basis_pairs
