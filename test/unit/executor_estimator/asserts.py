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

"""Standalone assertion helpers for client-side estimator tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from samplomatic.quantum_program import SamplexItem

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub

    from qiskit_ibm_runtime.quantum_program import QuantumProgram
    from test.unit.executor_estimator.utils import SamplexCircuitScenario, TemplateCircuitScenario


def assert_samplex_arguments_are_correct(
    item: SamplexItem,
    scenario: SamplexCircuitScenario,
    inject_noise: bool,
) -> None:
    """Assert that a :class:`~.SamplexItem`'s samplex arguments have the expected structure.

    Checks:

    * ``parameter_values`` is present iff ``scenario.has_parameter_values``.
    * Exactly ``scenario.num_basis_changes`` keys start with ``basis_changes.``.
    * Exactly ``scenario.num_basis_changes - 1`` ``basis_changes.*`` keys are all-zero arrays
      (mid-circuit measurement boxes), and exactly one is non-zero (the final measurement box).
    * When ``inject_noise`` is ``True`` (PEA, PEC): exactly ``scenario.num_noise_maps``
      ``noise_scales.*`` keys and the same number of ``pauli_lindblad_maps.*`` keys exist.
    * When ``inject_noise`` is ``False`` (vanilla, ZNE): no ``noise_scales.*`` or
      ``pauli_lindblad_maps.*`` keys exist.

    Args:
        item: The :class:`~.SamplexItem` to inspect.
        scenario: The :class:`SamplexCircuitScenario` whose PUB was used to produce ``item``.
        inject_noise: ``True`` for methods that inject noise (PEA, PEC); ``False`` for methods
            that do not (vanilla, ZNE).
    """
    keys = list(item.samplex_arguments)
    basis_keys = [k for k in keys if k.startswith("basis_changes.")]
    noise_keys = [k for k in keys if k.startswith("noise_scales.")]
    plm_keys = [k for k in keys if k.startswith("pauli_lindblad_maps.")]

    assert ("parameter_values" in keys) == scenario.has_parameter_values, (
        f"[{scenario.label}] parameter_values presence mismatch; keys={keys}"
    )
    if scenario.has_parameter_values:
        expected_pv = scenario.pub.parameter_values.as_array(scenario.pub.circuit.parameters)
        actual_pv = np.squeeze(np.asarray(item.samplex_arguments["parameter_values"]))
        assert np.array_equal(actual_pv, np.squeeze(expected_pv)), (
            f"[{scenario.label}] parameter_values mismatch; "
            f"got {actual_pv!r}, expected {np.squeeze(expected_pv)!r}"
        )
    assert len(basis_keys) == scenario.num_basis_changes, (
        f"[{scenario.label}] expected {scenario.num_basis_changes} "
        f"basis_changes key(s), got {len(basis_keys)}; keys={keys}"
    )
    zero_bc_keys = [k for k in basis_keys if np.all(np.asarray(item.samplex_arguments[k]) == 0)]
    nonzero_bc_keys = [
        k for k in basis_keys if not np.all(np.asarray(item.samplex_arguments[k]) == 0)
    ]
    assert len(zero_bc_keys) == scenario.num_basis_changes - 1, (
        f"[{scenario.label}] expected {scenario.num_basis_changes - 1} all-zero "
        f"basis_changes key(s) (mid-circuit boxes), got {len(zero_bc_keys)}; "
        f"keys={basis_keys}"
    )
    assert len(nonzero_bc_keys) == 1, (
        f"[{scenario.label}] expected exactly 1 non-zero basis_changes key "
        f"(final measurement box), got {len(nonzero_bc_keys)}; keys={basis_keys}"
    )
    if inject_noise:
        assert len(noise_keys) == scenario.num_noise_maps, (
            f"[{scenario.label}] expected {scenario.num_noise_maps} noise_scales "
            f"key(s), got {len(noise_keys)}; keys={keys}"
        )
        assert len(plm_keys) == scenario.num_noise_maps, (
            f"[{scenario.label}] expected {scenario.num_noise_maps} "
            f"pauli_lindblad_maps key(s), got {len(plm_keys)}; keys={keys}"
        )
    else:
        assert noise_keys == [], f"[{scenario.label}] noise_scales must be absent; keys={keys}"
        assert plm_keys == [], f"[{scenario.label}] pauli_lindblad_maps must be absent; keys={keys}"


def assert_template_circuit_is_correct(
    item: SamplexItem,
    scenario: TemplateCircuitScenario,
    enable_gates: bool,
    noise_factor: int = 1,
) -> None:
    """Assert that the template circuit inside a :class:`~.SamplexItem` has the expected shape.

    Checks:

    * ``item.circuit.num_clbits`` matches ``scenario.expected_num_clbits``.
    * ``item.circuit.num_parameters`` is consistent with the twirling options and ``noise_factor``.
      When ``enable_gates=True``, gate-folding scales the gate-twirling parameters while the
      measurement-box parameters stay fixed.  ``noise_factor=1`` is the unfolded baseline, so each
      additional unit adds ``scenario.num_parameters_per_noise_factor`` parameters::

          expected = num_circuit_parameters_gates_on
                     + num_parameters_per_noise_factor * (noise_factor - 1)

      When ``enable_gates=False`` the noise factor does not apply and the expected count is
      ``scenario.num_circuit_parameters_gates_off``.

    Args:
        item: The :class:`~.SamplexItem` to inspect.
        scenario: The :class:`TemplateCircuitScenario` whose PUB was used to produce ``item``.
        enable_gates: Whether gate twirling was enabled for this prepare call.
        noise_factor: The ZNE gate-folding noise factor (default ``1``, i.e. no folding).  Only
            meaningful when ``enable_gates=True``.
    """
    circuit = item.circuit
    if enable_gates:
        expected_num_params = (
            scenario.num_circuit_parameters_gates_on
            + scenario.num_parameters_per_noise_factor * (noise_factor - 1)
        )
    else:
        expected_num_params = scenario.num_circuit_parameters_gates_off

    assert circuit.num_clbits == scenario.expected_num_clbits, (
        f"[{scenario.label}] template num_clbits mismatch; "
        f"got {circuit.num_clbits}, expected {scenario.expected_num_clbits}"
    )
    assert circuit.num_parameters == expected_num_params, (
        f"[{scenario.label}] template num_parameters mismatch "
        f"(enable_gates={enable_gates}, noise_factor={noise_factor}); "
        f"got {circuit.num_parameters}, expected {expected_num_params}"
    )


def assert_trex_item_is_correct(
    program: QuantumProgram,
    pubs: Sequence[EstimatorPub],
    expected_num_randomizations: int,
) -> None:
    """Assert that a TREX calibration item was correctly added to a :class:`~.QuantumProgram`.

    Checks:

    * The last item is a :class:`~.SamplexItem`.
    * ``trex_item.shape == (expected_num_randomizations,)``.
    * ``trex_item.circuit.num_qubits`` equals ``max(pub.circuit.num_qubits for pub in pubs)``.
    * Every qubit has exactly one ``measure`` instruction — the circuit measures all qubits.
    * The gate counts are exactly ``3 * n`` ``rz`` and ``2 * n`` ``sx`` for ``n`` qubits, with no
      other non-barrier, non-measure gates.
    * ``passthrough_data["qiskit_mitigation"]`` contains an entry with ``mitigation == "trex"``,
      confirming the library registered the calibration circuit.

    Args:
        program: The :class:`~.QuantumProgram` returned by the prepare function.
        pubs: The PUBs passed to the prepare function, used to derive the expected TREX circuit
            width.
        expected_num_randomizations: The expected randomization count encoded in
            ``trex_item.shape[0]``.
    """
    trex_item = program.items[-1]
    assert isinstance(trex_item, SamplexItem), "Last item must be a SamplexItem (TREX)"

    assert trex_item.shape == (expected_num_randomizations,), (
        f"Expected TREX item shape ({expected_num_randomizations},), got {trex_item.shape}"
    )

    n = max(pub.circuit.num_qubits for pub in pubs)
    assert trex_item.circuit.num_qubits == n, (
        f"Expected TREX circuit width {n}, got {trex_item.circuit.num_qubits}"
    )

    op_counts = trex_item.circuit.count_ops()
    assert op_counts["measure"] == n, (
        f"Expected {n} measure operations (one per qubit), got {op_counts['measure']}"
    )
    assert op_counts["rz"] == 3 * n, (
        f"Expected {3 * n} rz operations (3 per qubit), got {op_counts['rz']}"
    )
    assert op_counts["sx"] == 2 * n, (
        f"Expected {2 * n} sx operations (2 per qubit), got {op_counts['sx']}"
    )
    assert set(op_counts) - {"barrier"} == {"measure", "rz", "sx"}, (
        f"Expected exactly gate types {{measure, rz, sx}} (plus barriers),got {dict(op_counts)}"
    )

    qm_entries = program.passthrough_data.get("qiskit_mitigation", [])  # type: ignore[union-attr]
    has_trex_entry = any(e.get("mitigation") == "trex" for e in qm_entries)
    assert has_trex_entry, "passthrough_data['qiskit_mitigation'] must contain a 'trex' entry"
