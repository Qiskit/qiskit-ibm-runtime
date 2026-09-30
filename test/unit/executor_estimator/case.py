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

"""Custom TestCase for client-side estimator tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from test.ibm_test_case import IBMTestCase

from .asserts import (
    assert_samplex_arguments_are_correct,
    assert_template_circuit_is_correct,
    assert_trex_item_is_correct,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from samplomatic.quantum_program import SamplexItem

    from qiskit_ibm_runtime.quantum_program import QuantumProgram
    from test.unit.executor_estimator.utils import SamplexCircuitScenario, TemplateCircuitScenario


class IBMEstimatorPrepareTestCase(IBMTestCase):
    """TestCase with assertions for estimator prepare-function tests."""

    def assertSamplexArgumentsAreCorrect(
        self,
        item: SamplexItem,
        scenario: SamplexCircuitScenario,
        inject_noise: bool,
    ) -> None:
        """Assert that a :class:`~.SamplexItem`'s samplex arguments have the expected structure.

        Checks:

        * ``parameter_values`` is present iff ``scenario.has_parameter_values``.
        * Exactly ``scenario.num_basis_changes`` keys start with ``basis_changes.``.
        * Exactly ``scenario.num_basis_changes - 1`` ``basis_changes.*`` keys are
          all-zero arrays (mid-circuit measurement boxes), and exactly one is
          non-zero (the final measurement box).
        * When ``inject_noise`` is ``True`` (PEA, PEC): exactly
          ``scenario.num_noise_maps`` ``noise_scales.*`` keys and the same number
          of ``pauli_lindblad_maps.*`` keys exist.
        * When ``inject_noise`` is ``False`` (vanilla, ZNE): no ``noise_scales.*``
          or ``pauli_lindblad_maps.*`` keys exist.

        Args:
            item: The :class:`~.SamplexItem` to inspect.
            scenario: The :class:`SamplexCircuitScenario` whose PUB was used to
                produce ``item``.
            inject_noise: ``True`` for methods that inject noise (PEA, PEC);
                ``False`` for methods that do not (vanilla, ZNE).
        """
        assert_samplex_arguments_are_correct(item, scenario, inject_noise)

    def assertTemplateCircuitIsCorrect(
        self,
        item: SamplexItem,
        scenario: TemplateCircuitScenario,
        enable_gates: bool,
        noise_factor: int = 1,
    ) -> None:
        """Assert that the template circuit inside a :class:`~.SamplexItem` has the expected shape.

        Checks:

        * ``item.circuit.num_clbits`` matches ``scenario.expected_num_clbits``.
        * ``item.circuit.num_parameters`` is consistent with the twirling options and
          ``noise_factor``.  When ``enable_gates=True``, gate-folding scales the gate-twirling
          parameters while the measurement-box parameters stay fixed.  ``noise_factor=1``
          is the unfolded baseline, so each additional unit adds
          ``scenario.num_parameters_per_noise_factor`` parameters::

              expected = num_circuit_parameters_gates_on
                         + num_parameters_per_noise_factor * (noise_factor - 1)

          When ``enable_gates=False`` the noise factor does not apply and the expected
          count is ``scenario.num_circuit_parameters_gates_off``.

        Args:
            item: The :class:`~.SamplexItem` to inspect.
            scenario: The :class:`TemplateCircuitScenario` whose PUB was used to
                produce ``item``.
            enable_gates: Whether gate twirling was enabled for this prepare call.
            noise_factor: The ZNE gate-folding noise factor (default ``1``, i.e. no
                folding).  Only meaningful when ``enable_gates=True``.
        """
        assert_template_circuit_is_correct(item, scenario, enable_gates, noise_factor)

    def assertTrexItemIsCorrect(
        self,
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
        * The gate counts are exactly ``3 * n`` ``rz`` and ``2 * n`` ``sx`` for ``n`` qubits,
          with no other non-barrier, non-measure gates.
        * ``passthrough_data["qiskit_mitigation"]`` contains an entry with
          ``mitigation == "trex"``, confirming the library registered the calibration circuit.

        Args:
            program: The :class:`~.QuantumProgram` returned by the prepare function.
            pubs: The PUBs passed to the prepare function, used to derive the expected
                TREX circuit width.
            expected_num_randomizations: The expected randomization count encoded in
                ``trex_item.shape[0]``.
        """
        assert_trex_item_is_correct(program, pubs, expected_num_randomizations)
