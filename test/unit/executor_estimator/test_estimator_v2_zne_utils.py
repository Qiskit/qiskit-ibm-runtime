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

"""Unit tests for EstimatorV2 ZNE helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from ddt import data, ddt, unpack
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp
from samplomatic.quantum_program import QuantumProgram, SamplexItem

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions
from qiskit_ibm_runtime.options_models.zne import ZneOptions

from ...ibm_test_case import IBMEstimatorPrepareTestCase
from ...utils import combine
from .utils import (
    PARAM_BASIS_3Q_SCENARIOS,
    SAMPLEX_CIRCUIT_SCENARIOS,
    TEMPLATE_CIRCUIT_SCENARIO,
    TWIRLING_SHAPE_SCENARIOS,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.primitives.containers.estimator_pub import EstimatorPubLike

# ---------------------------------------------------------------------------
# Helper: build EstimatorOptions from old-style args and call prepare()
# ---------------------------------------------------------------------------


def _prepare_zne(
    pubs: Iterable[EstimatorPubLike],
    twirling_options: TwirlingOptions,
    shots: int,
    zne_options: ZneOptions,
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
    add_tags: bool = False,
) -> QuantumProgram:
    """Drop-in for the old ``prepare_zne`` that delegates to ``prepare()``."""
    opts = EstimatorOptions()
    opts.twirling = twirling_options
    opts.resilience.zne_mitigation = True
    opts.resilience.zne = zne_options
    opts.resilience.measure_mitigation = measure_noise_learning is not None
    if measure_noise_learning is not None:
        opts.resilience.measure_noise_learning = measure_noise_learning
    opts.default_shots = shots
    qp, _ = prepare(pubs, opts, precision=None, add_tags=add_tags)
    return qp


@ddt
class TestPrepareZne(IBMEstimatorPrepareTestCase):
    """Tests for the ZNE prepare path."""

    @data([True, True, True], [False, True, True], [False, False, False])
    @unpack
    def test_param_basis_expansion_3q(
        self, enable_gates, enable_measure, enable_measure_noise_learning
    ):
        """Test parameter-basis expansion with three-qubit observables."""
        # TREX (measure_mitigation=True) rejects projection operators — use pure-Pauli
        # observables when measure_noise_learning is enabled.
        observables = (
            PARAM_BASIS_3Q_SCENARIOS.observables_pauli
            if enable_measure_noise_learning
            else PARAM_BASIS_3Q_SCENARIOS.observables_with_projectors
        )
        num_qubits = observables.num_qubits

        circuit = QuantumCircuit(num_qubits)
        circuit.rz(Parameter("alpha"), 0)

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        for scenario in PARAM_BASIS_3Q_SCENARIOS.scenarios:
            parameter_shape = scenario.parameter_shape
            observables_shape = scenario.observables_shape
            expected_pairs = scenario.expected_pairs

            with self.subTest(value=(parameter_shape, observables_shape, expected_pairs)):
                pub_like = (
                    circuit,
                    observables.reshape(observables_shape),
                    np.random.random(parameter_shape + (circuit.num_parameters,)),
                )
                pubs = [EstimatorPub.coerce(pub_like)]

                program = _prepare_zne(
                    pubs=pubs,
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=ZneOptions(),
                    measure_noise_learning=measure_noise_learning,
                )

                # param_basis_pairs now lives in the qiskit_mitigation passthrough block.
                param_basis_pairs = program.passthrough_data["qiskit_mitigation"][0][
                    "param_basis_pairs"
                ]

                # Check that the param-basis pairs are the correct ones
                self.assertListEqual(param_basis_pairs, expected_pairs, msg=param_basis_pairs)

                # Check that the quantum program has one element per param-basis pair
                self.assertEqual(program.items[0].shape, (1, len(expected_pairs)))

    @data(
        [True, True, True],
        [False, True, True],
        [False, False, False],
        [True, False, False],
        [False, True, False],
        [True, True, False],
    )
    @unpack
    def test_samplex_arguments_structure(
        self, enable_gates, enable_measure, enable_measure_noise_learning
    ):
        """Test that samplex arguments have the expected structure for each circuit type."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = [1, 3, 5]

        for scenario in SAMPLEX_CIRCUIT_SCENARIOS:
            with self.subTest(circuit=scenario.label):
                program = _prepare_zne(
                    pubs=[scenario.pub],
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=zne_options,
                    measure_noise_learning=measure_noise_learning,
                )
                # One item per noise factor; skip any trailing TREX item.
                for item in program.items[: len(zne_options.noise_factors)]:
                    self.assertSamplexArgumentsAreCorrect(item, scenario, inject_noise=False)

    @combine(enable_gates=[True, False], enable_measure=[True, False])
    def test_template_circuit(self, enable_gates, enable_measure):
        """Test that the template circuit has the expected clbits and parameter count."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = [1, 3, 5]

        scenario = TEMPLATE_CIRCUIT_SCENARIO
        program = _prepare_zne(
            pubs=[scenario.pub],
            twirling_options=twirling_options,
            shots=10,
            zne_options=zne_options,
        )
        # One item per noise factor; verify that the template scales correctly.
        for noise_factor, item in zip(
            zne_options.noise_factors, program.items[: len(zne_options.noise_factors)]
        ):
            with self.subTest(noise_factor=noise_factor):
                self.assertTemplateCircuitIsCorrect(
                    item, scenario, enable_gates=enable_gates, noise_factor=noise_factor
                )

    def test_prepare_zne_basic(self):
        """Test prepare_zne with basic ZNE options."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1.0, 2.0, 3.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = _prepare_zne([pub], TwirlingOptions(), shots, zne_options)

        self.assertIsInstance(quantum_program, QuantumProgram)
        # Should have len(noise_factors) items for the single pub
        self.assertEqual(len(quantum_program.items), len(noise_factors))

        for item in quantum_program.items:
            self.assertIsInstance(item, SamplexItem)

    @data("gate_folding", "gate_folding_front", "gate_folding_back")
    def test_prepare_zne_with_different_folding_methods(self, folding_method):
        """Test prepare_zne with different folding methods."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = folding_method
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = _prepare_zne([pub], TwirlingOptions(), shots, zne_options)

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(len(quantum_program.items), len(noise_factors))

    @data(32, "auto")
    def test_prepare_zne_with_measure_noise_learning(self, num_randomizations):
        """Test that measure_noise_learning adds a correctly built TREX calibration item."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)
        circuit2 = QuantumCircuit(3)
        circuit2.h(0)
        circuit2.cx(0, 1)
        circuit2.cx(1, 2)

        pub1 = EstimatorPub.coerce((circuit1, SparsePauliOp.from_list([("ZZ", 1)])))
        pub2 = EstimatorPub.coerce((circuit2, SparsePauliOp.from_list([("ZZZ", 1)])))
        pubs = [pub1, pub2]

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True
        twirling_options.num_randomizations = 64

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = num_randomizations

        program = _prepare_zne(
            pubs, twirling_options, 1024, zne_options, measure_noise_learning=measure_noise_learning
        )

        # 2 pubs * 2 noise_factors + 1 TREX calibration item.
        self.assertEqual(len(program.items), len(pubs) * len(noise_factors) + 1)
        expected_trex_randomizations = (
            twirling_options.num_randomizations
            if num_randomizations == "auto"
            else num_randomizations
        )
        self.assertTrexItemIsCorrect(
            program, pubs, expected_num_randomizations=expected_trex_randomizations
        )

    def test_prepare_zne_raises_error_with_less_than_2_noise_factors(self):
        """Test that prepare_zne raises when noise_factors has less than 2 points."""
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        with self.assertRaisesRegex(ValueError, "Must have at least two noise factors"):
            zne_options.noise_factors = [1.5]

    def test_prepare_zne_raises_error_with_too_few_noise_factors_for_extrapolator(self):
        """Test that prepare_zne rejects noise_factors under-specified for the extrapolator."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()

        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.extrapolator = "double_exponential"
        zne_options.noise_factors = [1.0, 3.0]

        with self.assertRaisesRegex(
            IBMInputValueError, "double_exponential requires at least 4 noise_factors"
        ):
            _prepare_zne([pub], twirling_options, 100, zne_options)

    def test_shapes_twirling_configs(self):
        """Verify the number of randomizations and program.shots."""
        noise_factors = [1.0, 3.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors

        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        pub = EstimatorPub.coerce((qc, SparsePauliOp.from_list([("ZZ", 1)])))

        for scenario in TWIRLING_SHAPE_SCENARIOS:
            with self.subTest(twirling=scenario.label):
                program = _prepare_zne(
                    pubs=[pub],
                    twirling_options=scenario.twirling_options,
                    shots=scenario.shots,
                    zne_options=zne_options,
                )
                self.assertEqual(
                    len(program.items),
                    len(noise_factors),
                    msg=f"[{scenario.label}] expected {len(noise_factors)} items, "
                    f"got {len(program.items)}",
                )
                for item in program.items:
                    self.assertEqual(
                        item.shape[0],
                        scenario.expected_num_randomizations,
                        msg=f"[{scenario.label}] expected R="
                        f"{scenario.expected_num_randomizations}, "
                        f"got {item.shape[0]}",
                    )
                self.assertEqual(
                    program.shots,
                    scenario.expected_shots_per_randomization,
                    msg=f"[{scenario.label}] expected program.shots="
                    f"{scenario.expected_shots_per_randomization}, got {program.shots}",
                )
