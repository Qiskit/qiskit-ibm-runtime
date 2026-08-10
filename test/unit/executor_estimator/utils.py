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
    """A single circuit scenario for testing the samplex arguments of a SamplexItem.

    Each scenario pairs an :class:`~qiskit.primitives.EstimatorPub` with the
    structural properties that its corresponding :class:`~.SamplexItem` samplex
    arguments must satisfy, regardless of which ``prepare_*`` function or twirling
    options are used.
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

    Depends on the number of mid-circuit measurement boxes in the circuit.
    """

    num_noise_maps: int = 0
    """Expected number of ``noise_scales.*`` / ``pauli_lindblad_maps.*`` key pairs,
    when noise injection is on.
    """


@dataclass(frozen=True)
class TemplateCircuitScenario:
    """A single circuit scenario for testing the template circuit produced by ``prepare_*``.

    Captures the structural properties of the compiled template circuit (number of
    classical bits and number of circuit parameters under different twirling options).
    """

    label: str
    """Human-readable name used in assertion messages."""

    pub: EstimatorPub
    """The estimator PUB whose template circuit will be inspected."""

    expected_num_clbits: int
    """Expected number of classical bits in the template circuit.

    Equal to ``original_qubits + original_clbits``.
    """

    num_circuit_parameters_gates_on: int
    """Expected ``template.num_parameters`` when ``twirling_options.enable_gates=True``
    and ``noise_factor=1`` (no gate folding).

    Depends on the topology of the circuit and the boxing strategy.
    ``enable_measure`` does not affect this count.
    """

    num_circuit_parameters_gates_off: int
    """Expected ``template.num_parameters`` when ``twirling_options.enable_gates=False``.

    Depends on the measurements and parameterized gates in the circuit, and the boxing
    strategy. ``enable_measure`` does not affect this count.
    """

    num_parameters_per_noise_factor: int
    """Number of template parameters added per unit increase in ZNE gate-folding noise factor.

    Only relevant for ZNE with gate folding (``amplifier="gate_folding*"``), which always
    runs with ``enable_gates=True``.  Gate folding repeats each 2-qubit gate block, so only
    the gate-twirling parameters scale; measurement-box parameters are fixed.  This field
    stores exactly the gate-twirling parameter count::

        num_parameters_per_noise_factor
            = num_circuit_parameters_gates_on - <measurement-box parameters>

    ``noise_factor=1`` is the unfolded baseline, so the expected total at a given
    ``noise_factor`` is::

        expected = num_circuit_parameters_gates_on
                   + num_parameters_per_noise_factor * (noise_factor - 1)
    """


def _make_samplex_circuit_scenarios() -> list[SamplexCircuitScenario]:
    obs2 = SparsePauliOp.from_list([("ZZ", 1)])
    obs3 = SparsePauliOp.from_list([("ZZZ", 1)])

    # non-parametric: no parameters, no mid-circuit measurements
    qc_non_parametric = QuantumCircuit(2)
    qc_non_parametric.h(0)
    qc_non_parametric.cx(0, 1)

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
            label="non_parameteric",
            pub=EstimatorPub.coerce((qc_non_parametric, obs2)),
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

Covers: non-parametric, parametric, mid-circuit measurement, and multi-layer (two
distinct noise-injected gate layers).
"""


def _make_template_circuit_scenario() -> TemplateCircuitScenario:
    # Circuit with two CX gates and a parametric RZ before the mid-circuit
    # measurement, then a single-qubit H after it.  Placing both 2Q gates
    # before the measurement means the circuit works under all twirling
    # combinations (enable_gates=False + enable_measure=True with a CX *after*
    # a mid-circuit measurement is not yet supported by samplomatic, #361).
    qc = QuantumCircuit(2, 1)
    qc.cx(0, 1)
    qc.rz(Parameter("theta"), 0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.h(0)

    obs = SparsePauliOp.from_list([("ZZ", 1)])

    return TemplateCircuitScenario(
        label="template_2q_param_midmeas",
        pub=EstimatorPub.coerce((qc, obs, np.array([[0.5]]))),
        # 2 qubit measurement bits + 1 original clbit = 3
        expected_num_clbits=3,
        # enable_gates=True: gate box cx(0,1) (2q=6) + gate box cx(0,1) (2q=6)
        #   + mid-meas box (2q=6) + final-meas box (2q=6) = 24
        #   (each CX instance gets its own box; theta is absorbed into the first)
        num_circuit_parameters_gates_on=24,
        # enable_gates=False: theta free (1) + mid-meas box (1q active accum=3)
        #   + final-meas box (2q=6) = 10
        num_circuit_parameters_gates_off=10,
        # gate-twirling params (per noise factor): gates_on - meas_params = 24 - 12 = 12
        # where meas params = mid-meas box (2q=6) + final-meas box (2q=6) = 12
        num_parameters_per_noise_factor=12,
    )


TEMPLATE_CIRCUIT_SCENARIO: TemplateCircuitScenario = _make_template_circuit_scenario()
"""Single template-circuit scenario for template circuit tests.

The circuit combines all three structural features exercised by template compilation:
a CX gate (2Q), a parametric RZ gate, a mid-circuit measurement, and a second CX
after the measurement.
"""
