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

"""Utils for EstimatorV2 unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub, ObservablesArray
from qiskit.quantum_info import SparsePauliOp

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem

    from ...ibm_test_case import IBMTestCase


@dataclass(frozen=True)
class ParamBasisScenario:
    """A single parameter-basis expansion scenario."""

    parameter_shape: tuple[int, ...]
    """The shape of the array of parameter values."""

    observables_shape: tuple[int, ...]
    """The shape of the observables array."""

    expected_pairs: Sequence[tuple[tuple[int, ...], str]]
    """Expected mapping from each parameter index to the observable(s) assigned after
    broadcasting the parameter and basis dimensions."""


@dataclass(frozen=True)
class ParamBasisScenarios:
    """A collection of scenarios to test parameter-basis expansion."""

    observables: ObservablesArray
    """The observables array used in these scenarios."""

    scenarios: Sequence[ParamBasisScenario]
    """A collection of scenarios."""


PARAM_BASIS_3Q_SCENARIOS = ParamBasisScenarios(
    observables=ObservablesArray(["Z0Z", "X+-", "lrY", "IrI"]),
    scenarios=[
        ParamBasisScenario(
            parameter_shape=(2, 2),
            observables_shape=(2, 2),
            expected_pairs=[((0, 0), "ZZZ"), ((0, 1), "XXX"), ((1, 0), "YYY"), ((1, 1), "IYI")],
        ),
        ParamBasisScenario(
            parameter_shape=(2, 2),
            observables_shape=(2, 2, 1),
            expected_pairs=[
                ((0, 0), "ZZZ"),
                ((0, 0), "YYY"),
                ((0, 1), "ZZZ"),
                ((0, 1), "YYY"),
                ((1, 0), "XXX"),
                ((1, 0), "IYI"),
                ((1, 1), "XXX"),
                ((1, 1), "IYI"),
            ],
        ),
        ParamBasisScenario(
            parameter_shape=(2, 2, 1),
            observables_shape=(2, 2),
            expected_pairs=[
                ((0, 0, 0), "ZZZ"),
                ((0, 0, 0), "XXX"),
                ((0, 1, 0), "YYY"),
                ((1, 0, 0), "ZZZ"),
                ((1, 0, 0), "XXX"),
                ((1, 1, 0), "YYY"),
            ],
        ),
        ParamBasisScenario(
            parameter_shape=(),
            observables_shape=(2, 2),
            expected_pairs=[((), "ZZZ"), ((), "XXX"), ((), "YYY")],
        ),
    ],
)
"""Scenarios to test parameter-basis expansion with three-qubit observables."""


@dataclass(frozen=True)
class SamplexCircuitScenario:
    """A single circuit scenario for testing samplex argument structure.

    Each scenario pairs an :class:`~qiskit.primitives.EstimatorPub` with the
    structural properties that its corresponding :class:`~.SamplexItem` must
    satisfy, regardless of which ``prepare_*`` function or twirling options are
    used.
    """

    label: str
    """Human-readable name used in :meth:`~unittest.TestCase.subTest` labels."""

    pub: EstimatorPub
    """The estimator PUB to feed into a ``prepare_*`` function."""

    has_parameter_values: bool
    """Whether the resulting samplex item must contain a ``parameter_values`` argument.

    ``True`` only for circuits that have free parameters.
    """

    num_basis_changes: int
    """Expected number of ``basis_changes.*`` keys in the samplex arguments.

    Depends on the number of mid-circuit boxes in the circuit.
    """

    num_noise_maps: int = 0
    """Expected number of ``noise_scales.*`` / ``pauli_lindblad_maps.*`` key pairs,
    when noise injection is on.
    """


def _make_samplex_circuit_scenarios() -> list[SamplexCircuitScenario]:
    obs2 = SparsePauliOp.from_list([("ZZ", 1)])
    obs3 = SparsePauliOp.from_list([("ZZZ", 1)])

    # regular: no parameters, no mid-circuit measurements
    qc_regular = QuantumCircuit(2)
    qc_regular.h(0)
    qc_regular.cx(0, 1)

    # parametric: one free parameter
    qc_parametric = QuantumCircuit(2)
    qc_parametric.rx(Parameter("theta"), 0)
    qc_parametric.cx(0, 1)

    # mid-circuit measurement
    qc_midcirc = QuantumCircuit(2, 1)
    qc_midcirc.h(0)
    qc_midcirc.cx(0, 1)
    qc_midcirc.measure(0, 0)
    qc_midcirc.h(0)

    # multi-layer: cx(0,1) repeated twice, then cx(1,2) repeated twice.
    # Produces 2 unique noise-injected layers (one per distinct gate topology),
    # even though there are 4 layers in total.
    qc_multilayer = QuantumCircuit(3)
    qc_multilayer.cx(0, 1)
    qc_multilayer.cx(0, 1)
    qc_multilayer.cx(1, 2)
    qc_multilayer.cx(1, 2)

    return [
        SamplexCircuitScenario(
            label="regular",
            pub=EstimatorPub.coerce((qc_regular, obs2)),
            has_parameter_values=False,
            num_basis_changes=1,
            num_noise_maps=1,
        ),
        SamplexCircuitScenario(
            label="parametric",
            pub=EstimatorPub.coerce((qc_parametric, obs2, np.array([[0.5]]))),
            has_parameter_values=True,
            num_basis_changes=1,
            num_noise_maps=1,
        ),
        SamplexCircuitScenario(
            label="mid-circuit",
            pub=EstimatorPub.coerce((qc_midcirc, obs2)),
            has_parameter_values=False,
            num_basis_changes=2,
            num_noise_maps=1,
        ),
        SamplexCircuitScenario(
            label="multi-layer",
            pub=EstimatorPub.coerce((qc_multilayer, obs3)),
            has_parameter_values=False,
            num_basis_changes=1,
            num_noise_maps=2,
        ),
    ]


SAMPLEX_CIRCUIT_SCENARIOS: list[SamplexCircuitScenario] = _make_samplex_circuit_scenarios()
"""Four circuit scenarios for samplex argument tests.

Covers: regular, parametric, mid-circuit measurement, and multi-layer (two
distinct noise-injected gate layers).
"""


def assert_samplex_item(
    test_case: IBMTestCase,
    item: SamplexItem,
    scenario: SamplexCircuitScenario,
    inject_noise: bool,
) -> None:
    """Assert that a :class:`~.SamplexItem`'s arguments match the expected structure.

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
        test_case: The running test case (provides assertion methods).
        item: The :class:`~.SamplexItem` to inspect.
        scenario: The :class:`SamplexCircuitScenario` whose PUB was used to
            produce ``item``.
        inject_noise: ``True`` for methods that inject noise (PEA, PEC);
            ``False`` for methods that do not (vanilla, ZNE).
    """
    keys = list(item.samplex_arguments)
    basis_keys = [k for k in keys if k.startswith("basis_changes.")]
    noise_keys = [k for k in keys if k.startswith("noise_scales.")]
    plm_keys = [k for k in keys if k.startswith("pauli_lindblad_maps.")]

    test_case.assertEqual(
        "parameter_values" in keys,
        scenario.has_parameter_values,
        msg=f"[{scenario.label}] parameter_values presence mismatch; keys={keys}",
    )
    if scenario.has_parameter_values:
        expected_pv = scenario.pub.parameter_values.as_array(scenario.pub.circuit.parameters)
        actual_pv = np.squeeze(np.asarray(item.samplex_arguments["parameter_values"]))
        test_case.assertTrue(
            np.array_equal(actual_pv, np.squeeze(expected_pv)),
            msg=(
                f"[{scenario.label}] parameter_values mismatch; "
                f"got {actual_pv!r}, expected {np.squeeze(expected_pv)!r}"
            ),
        )
    test_case.assertEqual(
        len(basis_keys),
        scenario.num_basis_changes,
        msg=(
            f"[{scenario.label}] expected {scenario.num_basis_changes} "
            f"basis_changes key(s), got {len(basis_keys)}; keys={keys}"
        ),
    )
    # Verify basis changes
    zero_bc_keys = [k for k in basis_keys if np.all(np.asarray(item.samplex_arguments[k]) == 0)]
    nonzero_bc_keys = [
        k for k in basis_keys if not np.all(np.asarray(item.samplex_arguments[k]) == 0)
    ]
    test_case.assertEqual(
        len(zero_bc_keys),
        scenario.num_basis_changes - 1,
        msg=(
            f"[{scenario.label}] expected {scenario.num_basis_changes - 1} all-zero "
            f"basis_changes key(s) (mid-circuit boxes), got {len(zero_bc_keys)}; "
            f"keys={basis_keys}"
        ),
    )
    test_case.assertEqual(
        len(nonzero_bc_keys),
        1,
        msg=(
            f"[{scenario.label}] expected exactly 1 non-zero basis_changes key "
            f"(final measurement box), got {len(nonzero_bc_keys)}; keys={basis_keys}"
        ),
    )
    if inject_noise:
        test_case.assertEqual(
            len(noise_keys),
            scenario.num_noise_maps,
            msg=(
                f"[{scenario.label}] expected {scenario.num_noise_maps} noise_scales "
                f"key(s), got {len(noise_keys)}; keys={keys}"
            ),
        )
        test_case.assertEqual(
            len(plm_keys),
            scenario.num_noise_maps,
            msg=(
                f"[{scenario.label}] expected {scenario.num_noise_maps} "
                f"pauli_lindblad_maps key(s), got {len(plm_keys)}; keys={keys}"
            ),
        )
    else:
        test_case.assertEqual(
            noise_keys,
            [],
            msg=f"[{scenario.label}] noise_scales must be absent; keys={keys}",
        )
        test_case.assertEqual(
            plm_keys,
            [],
            msg=f"[{scenario.label}] pauli_lindblad_maps must be absent; keys={keys}",
        )
