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

"""Helper functions for wrapper EstimatorV2.

NOTE: At least some of these functions are temporary and will be moved to a
permanent location (qiskit-addons or qiskit core) in the future.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    import numpy.typing as npt
    from qiskit import QuantumCircuit
    from qiskit.circuit import CircuitInstruction
    from qiskit.primitives import EstimatorPub
    from samplomatic.samplex import Samplex

    from ..options_models.measure_noise_learning_options import MeasureNoiseLearningOptions
    from ..options_models.twirling_options import TwirlingOptions

from collections import defaultdict
from functools import lru_cache

import numpy as np
from qiskit.circuit import ClassicalRegister
from qiskit.circuit.exceptions import CircuitError
from qiskit.quantum_info import Pauli, PauliList
from samplomatic import ChangeBasis
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions, get_annotation

from ..exceptions import IBMInputValueError

# Lookup table for converting Pauli characters to samplomatic integers
LOOKUP_TABLE = {"I": 0, "Z": 1, "X": 2, "Y": 3}


def get_pauli_basis(basis: str) -> Pauli:
    """Map computational basis to Pauli measurement basis.

    Converts basis strings like "000", "++0", "rl1" to Pauli operators.
    - 0, 1 → Z
    - +, - → X
    - r, l → Y
    - I → I

    Args:
        basis: Basis string to convert.

    Returns:
        Pauli operator representing the measurement basis.
    """
    basis = (
        basis.replace("0", "Z")
        .replace("1", "Z")
        .replace("+", "X")
        .replace("-", "X")
        .replace("r", "Y")
        .replace("l", "Y")
    )
    return Pauli(basis)


def pauli_to_ints(pauli: Pauli) -> list[int]:
    """Convert Pauli to list of ints following samplomatic convention.

    I→0, Z→1, X→2, Y→3

    Args:
        pauli: Pauli operator to convert.

    Returns:
        List of integers representing the Pauli.

    Note:
        pauli.to_label() returns big-endian (leftmost = highest qubit),
        but samplomatic expects little-endian (leftmost = qubit 0),
        so we reverse the list.
    """
    return [LOOKUP_TABLE[p] for p in pauli.to_label()][::-1]


def unbroadcast_index(
    bc_index: tuple[int | slice, ...], shape: tuple[int, ...]
) -> tuple[int | slice, ...]:
    """Index an array using an index from a compatible broadcasted shape.

    An ND-array ``arr`` is broadcastable to any shape ``bc_shape = (*pad_shape, *arr.shape)``.
    This function allows indexing ``arr`` using an ND-index or slice from ``bc_shape`` and
    will return the index for ``arr`` that accesses the same value.

    Args:
        bc_index: An ND-index from a broadcasted shape.
        shape: The shape of the broadcasting compatible array to index.

    Returns:
        The equivalent un-broadcasted ND-index of the array with specified shape.
    """

    @lru_cache
    def _pad_broadcast_shape(shape: tuple[int, ...], ndims: int) -> tuple[int | slice, ...]:
        # Pad a shape with trivial dimensions.
        shape_ndims = len(shape)
        pad = ndims - shape_ndims
        if pad > 0:
            return pad * (1,) + shape
        return shape

    shape_ndims = len(shape)
    if shape_ndims == 0:
        return ()

    pad_shape = _pad_broadcast_shape(shape, len(bc_index))
    bc_index = tuple(0 if dim == 1 else i for i, dim in zip(bc_index, pad_shape))
    return bc_index[-shape_ndims:]


def resolve_precision(
    pubs: list[EstimatorPub],
    run_precision: float | None = None,
) -> float | None:
    """Resolve precision from multiple sources with clear precedence.

    Precedence order (highest to lowest):
    1. Individual pub precision (must be consistent across all pubs)
    2. run() method precision parameter (run_precision)

    Args:
        pubs: List of estimator pubs (may contain precision values).
        run_precision: Precision specified in run() method.

    Returns:
        The resolved precision value, or None if no precision is specified anywhere.

    Raises:
        IBMInputValueError: If pubs have different precision values.
    """
    # Extract precision from pubs
    pub_precisions = {pub.precision if pub.precision is not None else run_precision for pub in pubs}

    if len(pub_precisions) != 1:
        raise IBMInputValueError(
            f"All pubs must have the same precision. Found: {pub_precisions}"
            "(possibly via the run provided precision parameter)"
        )

    if (precision := next(iter(pub_precisions))) is not None and precision <= 0:
        raise IBMInputValueError("The precision value must be strictly greater than 0.")

    return precision


def box_circuit(
    circuit: QuantumCircuit,
    enable_gates: bool,
    measure_annotations: str,
    twirling_strategy: str,
    inject_noise: bool = False,
    add_tags: Literal["none", "unique_box", "unique_instance", "noise_ref"] = "none",
) -> QuantumCircuit:
    """Group the operations in the given ``circuit`` into boxes.

    This function removes the final measurement layer from the given circuit and adds a new
    measurement layer with a dedicated register name. Then, it uses the
    :meth:`~samplomatic.transpiler.generate_boxing_pass_manager` to group the operations in a
    circuit into boxes.

    Args:
        circuit: The quantum circuit to box.
        enable_gates: Whether to group gates into boxes. This value is passed directly to the
            ``enable_gates`` argument of
            :meth:`~samplomatic.transpiler.generate_boxing_pass_manager`.
        measure_annotations: The annotations placed on the measurement boxes. The measurements
            are grouped into boxes by default, and the value of ``measure_annotations`` passed
            directly to the ``measure_annotations`` argument of
            :meth:`~samplomatic.transpiler.generate_boxing_pass_manager`. See the Samplomatic
            API docs for a full list of supported values.
        twirling_strategy: The strategy for whether and how twirling boxes are extended to
            include eligible idle qubits. This value is passed directly to the ``twirling_strategy``
            argument of
            :meth:`~samplomatic.transpiler.generate_boxing_pass_manager`. See the Samplomatic
            API docs for a full list of supported values.
        inject_noise: Whether to add :class:`~samplomatic.InjectNoise` annotations to the boxes
            of gates. If ``True``, :meth:`~samplomatic.transpiler.generate_boxing_pass_manager` is
            called with arguments ``inject_noise_targets`` and ``inject_noise_strategy`` set to
            ``"gates"`` and ``"uniform_modification"`` respectively; if ``False``, it is called with
            ``inject_noise_targets`` and ``inject_noise_strategy`` set to ``"none"`` and
            ``"no_modification"``. See the Samplomatic API docs for more details regarding these
            values.
        add_tags: Whether to include tags for the boxes.

    Returns:
        The boxed circuit.
    """
    # Remove any existing final measurements
    prepared_circuit = circuit.remove_final_measurements(inplace=False)

    # Add final measurements
    creg = ClassicalRegister(prepared_circuit.num_qubits, "_meas")
    try:
        prepared_circuit.add_register(creg)
    except CircuitError:
        raise IBMInputValueError("Name `_meas` is reserved for a dedicated classical register.")
    prepared_circuit.barrier()
    prepared_circuit.measure(prepared_circuit.qubits, creg)

    boxing_pm = generate_boxing_pass_manager(
        enable_gates=enable_gates,
        enable_measures=True,
        twirling_strategy=twirling_strategy,
        measure_annotations=measure_annotations,
        inject_noise_site="after",
        inject_noise_targets="gates" if inject_noise else "none",
        inject_noise_strategy="uniform_modification" if inject_noise else "no_modification",
        add_tags=add_tags,
    )
    boxed_circuit = boxing_pm.run(prepared_circuit)
    return boxed_circuit


def options_to_boxing_pm_kwargs(  # type: ignore[no-untyped-def]
    twirling_options: TwirlingOptions,
    measure_noise_learning: MeasureNoiseLearningOptions | None,
    inject_noise: bool,
    add_tags: bool = False,
) -> dict[str, Any]:
    """A helper to map options to kwargs for the boxing passmanager.

    Args:
        twirling_options: Twirling options.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be accounted for in boxing.
        inject_noise: Whether to inject noise.
        add_tags: Whether to include tags for the boxes. ``False`` will cause no tags to be added
            (will pass the "none" value to the relevant attribute), while ``True`` will cause tags
            with the twirled boxes hash to be added (using the "unique_box" value of the relevant
            attribute). These tags can help injecting noise in simulators.

    Returns:
        Options to the boxing passmanager.
    """
    return {
        "enable_gates": twirling_options.enable_gates or inject_noise,
        "measure_annotations": "all"
        if twirling_options.enable_measure or (measure_noise_learning is not None)
        else "change_basis",
        "twirling_strategy": twirling_options.strategy.replace("-", "_"),
        "inject_noise": inject_noise,
        "add_tags": "unique_box" if add_tags else "none",
    }


def find_unique_layers(
    pubs: Iterable[EstimatorPub],
    twirling_options: TwirlingOptions,
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
    inject_noise: bool = False,
    add_tags: bool = False,
) -> list[CircuitInstruction]:
    """Return the unique boxed layers found across the given PUBs.

    Args:
        pubs: The list of PUBs to return a list of unique boxes for.
        twirling_options: Twirling options.
        measure_noise_learning: The measure noise learning options. If provided, Twirled Readout
            Error eXtinction (TREX) mitigation method will be accounted for in boxing.
        inject_noise: Whether to add :class:`~samplomatic.InjectNoise` annotations to the boxes
            of gates.
        add_tags: Whether to include tags for the boxes. Relevant mainly for debugging.

    Returns:
        Unique boxed layers found across the given PUBs.
    """
    pm_kwargs = options_to_boxing_pm_kwargs(
        twirling_options,
        measure_noise_learning,
        inject_noise,
        add_tags=add_tags,
    )
    boxed_circuits = (box_circuit(circuit=pub.circuit, **pm_kwargs) for pub in pubs)
    instructions = (box for boxed_circuit in boxed_circuits for box in boxed_circuit)
    return find_unique_box_instructions(
        instructions=instructions, normalize_annotations=None, undress_boxes=True
    )


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
        3. It flattens the map into two 1D arrays of equal length, containing the subsets of
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


def make_samplex_arguments(
    samplex: Samplex,
    boxed_circuit: QuantumCircuit,
    flat_parameter_values: npt.NDArray[float],
    change_basis: npt.NDArray[int],
) -> dict[str, Any]:
    """Build a samplex args dictionary consisting of ``change_basis`` and parameters data.

    Args:
        samplex: A samplex object to create args to.
        boxed_circuit: A boxed circuit related to the samplex.
        flat_parameter_values: A flattened array of parameter values.
        change_basis: An array of bases to change.

    Returns:
        A samplex args dictionary.
    """
    # Prepare samplex_arguments
    samplex_arguments = {}
    if samplex.inputs().get_specs("parameter_values"):
        samplex_arguments["parameter_values"] = flat_parameter_values

    # Set changing basis gates
    for spec in samplex.inputs().get_specs("basis_changes"):
        # Default to np.zeros, to ensure that every mid-circuit measurement
        # that may be present is performed without basis changing gates
        samplex_arguments[spec.name] = np.zeros(spec.shape)

    # Finalize basis changing gates for the final measurements
    for instr in boxed_circuit.reverse_ops():
        op = instr.operation
        if op.name == "box" and (change_basis_annot := get_annotation(op, ChangeBasis)):
            samplex_arguments[f"basis_changes.{change_basis_annot.ref}"] = change_basis
            break
    else:
        # This should not be reachable
        raise ValueError("Could not find a change basis annotation.")

    return samplex_arguments
