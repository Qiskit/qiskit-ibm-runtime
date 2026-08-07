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

"""Utility functions for executor-based SamplerV2."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from qiskit.circuit import BoxOp, ClassicalRegister
from qiskit.circuit.exceptions import CircuitError
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from ..exceptions import IBMInputValueError

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from qiskit.circuit import CircuitInstruction, QuantumCircuit
    from qiskit.primitives.containers.sampler_pub import SamplerPub

    from ..options_models.twirling import TwirlingOptions


def validate_no_boxes(circuit: QuantumCircuit) -> None:
    """Validate that a circuit contains no :class:`~qiskit.circuit.BoxOp` instructions.

    Args:
        circuit: The circuit to validate.

    Raises:
        IBMInputValueError: If the circuit contains :class:`~qiskit.circuit.BoxOp` instructions.
    """
    for instruction in circuit.data:
        if isinstance(instruction.operation, BoxOp):
            raise IBMInputValueError(
                f"Circuit contains a BoxOp instruction '{instruction.operation.name}' "
                "which is not supported in this minimal implementation. "
                "BoxOp support (for twirling) will be added in a future phase."
            )


def validate_meas_type_twirling(meas_type: str | None, enable_measure: bool | None) -> None:
    """Validate measurement twirling is compatible with the requested ``meas_type``.

    Measurement twirling flips bits before measurement and XOR-corrects them in
    post-processing, which requires classified bit results. Kerneled returns are complex
    IQ data, so the correction cannot be applied.

    Args:
        meas_type: The requested measurement return type.
        enable_measure: Whether measurement twirling is enabled.

    Raises:
        IBMInputValueError: If ``enable_measure`` is set with a non-classified ``meas_type``.
    """
    if meas_type in {"kerneled", "avg_kerneled"} and enable_measure:
        raise IBMInputValueError(
            f"'meas_type={meas_type}' and measurement twirling are not compatible. "
            "Set `twirling.enable_measure=False` or `execution.meas_type='classified'`"
        )


def validate_twirling_option_fields_are_not_none(options: TwirlingOptions) -> None:
    """Validate that twirling options fields are not ``None``.

    Args:
        options: The options to validate

    Raises:
        IBMInputValueError: If ``options.enable_gates`` or ``options.enable_measure`` are ``None``.
    """
    if options.enable_gates is None:
        raise IBMInputValueError("``enable_gates`` is ``None``, expected ``True`` or ``False``.")
    if options.enable_measure is None:
        raise IBMInputValueError("``enable_measure`` is ``None``, expected ``True`` or ``False``.")


def extract_shots_from_pubs(pubs: Sequence[SamplerPub], default_shots: int | None = None) -> int:
    """Extract and validate shots value from a sequence of ``SamplerPub`` objects.

    This function determines the shots value by examining all pubs and ensures
    that all pubs have the same number of shots. If a pub doesn't specify shots,
    the default_shots value is used.

    Args:
        pubs: Sequence of sampler pubs to extract shots from.
        default_shots: Default number of shots if not specified in pubs.

    Returns:
        The validated shots value that all pubs share.

    Raises:
        IBMInputValueError: If shots are not specified
            anywhere, or if pubs have different shot values.
    """
    pub_shots = {pub.shots or default_shots for pub in pubs} if pubs else {default_shots}
    if None in pub_shots:
        raise IBMInputValueError("Shots must be specified either in the pub or as default_shots.")
    pub_shots = {s for s in pub_shots if s is not None}  # For mypy typing
    if len(pub_shots) != 1:
        raise IBMInputValueError(f"All pubs must have the same number of shots. Found: {pub_shots}")
    return next(iter(pub_shots))


def box_circuit(
    circuit: QuantumCircuit,
    enable_gates: bool,
    measure_annotations: str,
    twirling_strategy: str,
    twirling_group: str,
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
        inject_noise_targets="none",
        inject_noise_strategy="no_modification",
        add_tags=add_tags,
    )
    boxed_circuit = boxing_pm.run(prepared_circuit)
    return boxed_circuit


def options_to_boxing_pm_kwargs(  # type: ignore[no-untyped-def]
    twirling_options: TwirlingOptions,
    twirling_group: str = "balanced_pauli",
    add_tags: bool = False,
) -> dict[str, Any]:
    """A helper to map options to kwargs for the boxing passmanager.

    Args:
        twirling_options: Twirling options.
        twirling_group: The group to use for the twirling boxes.
        add_tags: Whether to include tags for the boxes. ``False`` will cause no tags to be added
            (will pass the "none" value to the relevant attribute), while ``True`` will cause tags
            with the twirled boxes hash to be added (using the "unique_box" value of the relevant
            attribute). These tags can help injecting noise in simulators.

    Returns:
        Options to the boxing passmanager.
    """
    return {
        "enable_gates": twirling_options.enable_gates,
        "measure_annotations": "all" if twirling_options.enable_measure else "change_basis",
        "twirling_strategy": twirling_options.strategy.replace("-", "_"),
        "twirling_group": twirling_group,
        "add_tags": "unique_box" if add_tags else "none",
    }


def find_unique_layers(
    pubs: Iterable[SamplerPub],
    twirling_options: TwirlingOptions,
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
        add_tags=add_tags,
    )
    boxed_circuits = (box_circuit(circuit=pub.circuit, **pm_kwargs) for pub in pubs)
    instructions = (box for boxed_circuit in boxed_circuits for box in boxed_circuit)
    return find_unique_box_instructions(
        instructions=instructions, normalize_annotations=None, undress_boxes=True
    )
