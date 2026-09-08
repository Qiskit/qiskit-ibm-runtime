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

"""Unit tests for EstimatorV2 prepare vanilla function."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from ddt import data, ddt, unpack
from qiskit import QuantumCircuit
from qiskit.circuit import ClassicalRegister, Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp
from samplomatic.quantum_program import SamplexItem

from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions

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
    from samplomatic.quantum_program import QuantumProgram

# ---------------------------------------------------------------------------
# Helper: build EstimatorOptions from old-style args and call prepare()
# ---------------------------------------------------------------------------


def _prepare_vanilla(
    pubs: Iterable[EstimatorPubLike],
    twirling_options: TwirlingOptions,
    shots: int,
    measure_noise_learning: MeasureNoiseLearningOptions | None = None,
    add_tags: bool = False,
) -> QuantumProgram:
    """Drop-in for the old ``prepare_vanilla`` that delegates to ``prepare()``.

    ``measure_mitigation`` is set only when ``measure_noise_learning`` is provided
    **and** the test observables do not contain projection operators (which are
    incompatible with the measure-mitigation post-processing path).  For the
    param-basis-expansion tests that combine projector observables with
    ``measure_noise_learning``, callers should pass ``measure_noise_learning=None``
    or use non-projector observables.
    """
    opts = EstimatorOptions()
    opts.twirling = twirling_options
    if measure_noise_learning is not None:
        opts.resilience.measure_mitigation = True
        opts.resilience.measure_noise_learning = measure_noise_learning
    else:
        opts.resilience.measure_mitigation = False
    opts.resilience.zne_mitigation = False
    opts.resilience.pec_mitigation = False
    opts.default_shots = shots
    qp, _ = prepare(pubs, opts, precision=None, add_tags=add_tags)
    return qp


@ddt
class TestPrepareVanilla(IBMEstimatorPrepareTestCase):
    """Tests for the vanilla prepare path (no mitigation)."""

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

                program = _prepare_vanilla(
                    pubs=pubs,
                    twirling_options=twirling_options,
                    shots=10,
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

        for scenario in SAMPLEX_CIRCUIT_SCENARIOS:
            with self.subTest(circuit=scenario.label):
                program = _prepare_vanilla(
                    pubs=[scenario.pub],
                    twirling_options=twirling_options,
                    shots=10,
                    measure_noise_learning=measure_noise_learning,
                )
                self.assertSamplexArgumentsAreCorrect(
                    program.items[0], scenario, inject_noise=False
                )

    @combine(enable_gates=[True, False], enable_measure=[True, False])
    def test_template_circuit(self, enable_gates, enable_measure):
        """Test that the template circuit has the expected clbits and parameter count."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        scenario = TEMPLATE_CIRCUIT_SCENARIO
        program = _prepare_vanilla(
            pubs=[scenario.pub],
            twirling_options=twirling_options,
            shots=10,
        )
        self.assertTemplateCircuitIsCorrect(program.items[0], scenario, enable_gates=enable_gates)

    @combine(enable_gates=[True, False], enable_measure=[True, False])
    def test_prepare_with_mid_circuit_measurements(self, enable_gates, enable_measure):
        """Test the prepare function for circuits with mid-circuit measurements."""
        if enable_measure or not (enable_gates or enable_measure):
            self.skipTest(
                "Mid-circuit measurements are not yet fully supported by samplomatic, see"
                "Samplomatic issue #361."
            )

        circuit = QuantumCircuit(3, 3)
        circuit.h(0)
        circuit.cx(0, 1)
        # Add mid-circuit measurement
        circuit.measure(0, 0)
        # Continue with more gates after measurement
        circuit.h(0)
        circuit.cx(0, 2)

        observable = SparsePauliOp.from_list([("ZZZ", 1), ("XXX", 1), ("YYY", 1), ("IZI", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure
        twirling_options.num_randomizations = 7
        twirling_options.strategy = "all"
        program = _prepare_vanilla(pubs=[pub], twirling_options=twirling_options, shots=1024)

        self.assertEqual(len(program.items), 1)
        self.assertIsInstance(program.items[0], SamplexItem)
        self.assertEqual(len(program.items[0].samplex.inputs().specs), 2)

        # 7 randomizations, 3 basis
        self.assertEqual(program.items[0].shape, (7 if enable_gates or enable_measure else 1, 3))

        # We expect two `basis_changes` specs, but can't be sure how they'll be ordered.
        # So we verify that we have exactly one of each expected specs.
        specs = program.items[0].samplex.inputs().specs
        for spec in specs:
            self.assertTrue(spec.name.startswith("basis_changes"))
            self.assertEqual(spec.shape, (3,))

        samplex_args = program.items[0].samplex_arguments
        mid_circuit_names = [
            name for name in samplex_args if np.array_equal(samplex_args[name], np.zeros(3))
        ]
        final_meas_names = [
            name
            for name in samplex_args
            if np.array_equal(samplex_args[name], np.array([[2, 2, 2], [3, 3, 3], [1, 1, 1]]))
        ]
        self.assertEqual(
            len(mid_circuit_names),
            1,
            msg=f"Expected 1 mid-circuit spec with zeros, got: {samplex_args}",
        )
        self.assertEqual(
            len(final_meas_names),
            1,
            msg=f"Expected 1 final-meas spec with change_basis, got: {samplex_args}",
        )

    def test_prepare_with_reserved_classical_register_name_raises(self):
        """Test that prepare raises error when circuit uses reserved classical register name."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        reserved_creg = ClassicalRegister(2, "_meas")
        circuit.add_register(reserved_creg)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaises(ValueError) as context:
            _prepare_vanilla([pub], twirling_options, 1024)

        self.assertIn("_meas", str(context.exception))
        self.assertIn("reserved", str(context.exception))

    @data(32, "auto")
    def test_prepare_with_measure_noise_learning(self, num_randomizations):
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

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True
        twirling_options.num_randomizations = 64

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = num_randomizations

        program = _prepare_vanilla(
            pubs, twirling_options, shots=1024, measure_noise_learning=measure_noise_learning
        )

        # Two estimation items (one per pub) + one TREX calibration item.
        self.assertEqual(len(program.items), 3)
        expected_trex_randomizations = (
            twirling_options.num_randomizations
            if num_randomizations == "auto"
            else num_randomizations
        )
        self.assertTrexItemIsCorrect(
            program, pubs, expected_num_randomizations=expected_trex_randomizations
        )

    def test_shapes_twirling_configs(self):
        """Verify the number of randomizations and program.shots."""
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        pub = EstimatorPub.coerce((qc, SparsePauliOp.from_list([("ZZ", 1)])))

        for scenario in TWIRLING_SHAPE_SCENARIOS:
            with self.subTest(twirling=scenario.label):
                program = _prepare_vanilla(
                    pubs=[pub],
                    twirling_options=scenario.twirling_options,
                    shots=scenario.shots,
                )
                item = program.items[0]
                self.assertEqual(
                    item.shape[0],
                    scenario.expected_num_randomizations,
                    msg=f"[{scenario.label}] expected R={scenario.expected_num_randomizations}, "
                    f"got {item.shape[0]}",
                )
                self.assertEqual(
                    program.shots,
                    scenario.expected_shots_per_randomization,
                    msg=f"[{scenario.label}] expected program.shots="
                    f"{scenario.expected_shots_per_randomization}, got {program.shots}",
                )
