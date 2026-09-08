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

from typing import TYPE_CHECKING, Any, Literal, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from qiskit import QuantumCircuit
    from qiskit.circuit import BoxOp, CircuitInstruction
    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from qiskit.primitives.containers.sampler_pub import SamplerPub

    from ..options_models.measure_noise_learning import MeasureNoiseLearningOptions
    from ..options_models.twirling import TwirlingOptions

from qiskit.circuit import ClassicalRegister
from qiskit.circuit.exceptions import CircuitError
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions, undress_box

from ..exceptions import IBMInputValueError

_REQUIRED_NOISE_FACTORS = {
    "linear": 2,
    "exponential": 2,
    "double_exponential": 4,
    "fallback": 1,
    **{f"polynomial_degree_{degree}": degree + 1 for degree in range(1, 8)},
}

# TypeAlias for a BoxOp type
BoxType: TypeAlias = Literal["gates", "measurement", "unknown"]


def validate_noise_factors(
    noise_factors: Sequence[float], extrapolator: str | Sequence[str]
) -> None:
    """Check that ``noise_factors`` has enough points for every requested extrapolator.

    Args:
        noise_factors: The resolved noise factors that will be used for amplification.
        extrapolator: The extrapolator(s) requested in the ZNE options.

    Raises:
        IBMInputValueError: If ``noise_factors`` is under-specified for any extrapolator.
    """
    extrapolators = [extrapolator] if isinstance(extrapolator, str) else extrapolator
    for extrap in extrapolators:
        required = _REQUIRED_NOISE_FACTORS[extrap]
        if len(noise_factors) < required:
            raise IBMInputValueError(f"{extrap} requires at least {required} noise_factors")


def has_projection_operators(pub: EstimatorPub) -> bool:
    """Return whether an estimator pub contains projection operators in its observables."""
    projection_set = set("01rl+-")
    for observable in pub.observables.ravel():
        for observable_term in observable:
            if bool(set(observable_term) & projection_set):
                return True
    return False


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
    twirling_group: str,
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
        twirling_group: The group to use for the twirling boxes.
            Check the :meth:`~.samplomatic.transpiler.generate_boxing_pass_manager` documentation
            for supported values.
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
        twirling_group=twirling_group,
        measure_annotations=measure_annotations,
        inject_noise_site="after",
        inject_noise_targets="gates" if inject_noise else "none",
        inject_noise_strategy="uniform_modification" if inject_noise else "no_modification",
        add_tags=add_tags,
    )
    boxed_circuit = boxing_pm.run(prepared_circuit)
    return boxed_circuit


def options_to_boxing_pm_kwargs(
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
        twirling_group: The group to use for the twirling boxes.
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
        "twirling_group": twirling_options.group,
        "inject_noise": inject_noise,
        "add_tags": "unique_box" if add_tags else "none",
    }


def find_unique_layers(
    pubs: Iterable[EstimatorPub | SamplerPub],
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
        add_tags: Whether to include tags for the boxes.

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


def find_box_type(instruction: BoxOp) -> BoxType:
    """Find the type of :class:`~qiskit.circuit.BoxOp` that ``instruction`` contains.

    Args:
        instruction: The instruction to get the type of.

    Returns:
        The box type. Can be one of ``"gates"``, ``"measurement"``, or ``"unknown"``.

    Raises:
        IBMInputValueError: If ``instruction`` does not contain a box.
    """
    box = instruction.operation
    if (name := box.name) != "box":
        raise IBMInputValueError(f"Expected a 'box' but found '{name}'.")

    undressed_box = undress_box(box)

    if len(undressed_box.body) == 0:
        return "gates"

    all_gates = all(op.is_standard_gate() or op.name == "barrier" for op in undressed_box.body)
    all_measurement = all(op.name in ["measure", "barrier"] for op in undressed_box.body)

    if all_gates and not all_measurement:
        return "gates"
    elif not all_gates and all_measurement:
        return "measurement"

    return "unknown"
