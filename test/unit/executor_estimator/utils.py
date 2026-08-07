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
