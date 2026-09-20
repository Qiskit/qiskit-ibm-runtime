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

"""Unit tests for Estimator prepare method."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, cast

import numpy as np
from ddt import data, ddt, unpack
from qiskit.circuit import ClassicalRegister, Parameter, QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp
from samplomatic import InjectNoise, Tag
from samplomatic.exceptions import BuildError
from samplomatic.quantum_program import SamplexItem
from samplomatic.utils import find_unique_box_instructions, get_annotation

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor.calculate_twirling_shots import calculate_twirling_shots
from qiskit_ibm_runtime.executor_estimator.prepare import prepare

# TODO: find_unique_layers is imported from the sampler module as a temporary workaround.
# The prepare() method internally uses
# qiskit_mitigation.find_combined_unique_layers. These two paths could silently produce
# different InjectNoise.ref values if they ever diverge. A permanent solution backed by
# the estimator's find_combined_unique_layers path is needed.
from qiskit_ibm_runtime.executor_sampler.utils import find_unique_layers
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.executor import ExecutorOptions
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.pec import PecOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions
from qiskit_ibm_runtime.options_models.zne import ZneOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMEstimatorPrepareTestCase, IBMTestCase
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


@ddt
class TestPrepare(IBMTestCase):
    """Test the ``prepare`` function."""

    @data("vanilla", "pec", "zne", "pea")
    def test_add_tags(self, path):
        """Test that ``prepare`` adds tags when ``add_tags=True``."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [(circuit, observable)]

        layers = find_unique_box_instructions(
            circuit,
            normalize_annotations=None,
            undress_boxes=True,
        )

        options = EstimatorOptions()
        options.twirling.enable_gates = True
        match path:
            case "vanilla":
                options.twirling.enable_measure = True
            case "pec":
                options.resilience.pec_mitigation = True
                options.resilience.layer_noise_model = [
                    (layer, PauliLindbladMap.identity(num_qubits=2)) for layer in layers
                ]
            case "zne":
                options.resilience.zne_mitigation = True
            case "pea":
                options.resilience.zne_mitigation = True
                options.resilience.zne.amplifier = "pea"
                options.resilience.layer_noise_model = [
                    (layer, PauliLindbladMap.identity(num_qubits=2)) for layer in layers
                ]

        program, _ = prepare(pubs, options, precision=0.1, add_tags=True)

        for item in program.items:
            unique_instructions = find_unique_box_instructions(item.circuit)
            for inst in unique_instructions:
                self.assertIsNotNone(get_annotation(inst.operation, Tag))

    def test_vanilla_path(self):
        """Test the ``prepare`` function when no mitigation is requested."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.twirling.enable_measure = True

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [(circuit, observable)]

        program, executor_options = prepare(pubs, options, precision=0.1)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        # Vanilla path: qiskit_mitigation passthrough contains MitigationTask entries.
        # The "mitigation" key no longer lives in post_processor; task type is encoded
        # in the qiskit_mitigation passthrough block instead.
        self.assertIn("qiskit_mitigation", program.passthrough_data)
        self.assertIn("post_processor", program.passthrough_data)

    def test_pec_path(self):
        """Test the ``prepare`` function when PEC is requested."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [(circuit, observable)]

        layers = find_unique_box_instructions(
            circuit,
            normalize_annotations=None,
            undress_boxes=True,
        )

        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.resilience.pec_mitigation = True
        options.resilience.layer_noise_model = [
            (layer, PauliLindbladMap.identity(num_qubits=2)) for layer in layers
        ]

        program, executor_options = prepare(pubs, options, precision=0.1)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        # PEC path: confirm passthrough has both namespaces and the qp has 2 items
        # (1 PEC data item + 1 TREX calibration item, since measure_mitigation is on by default).
        self.assertIn("qiskit_mitigation", program.passthrough_data)
        self.assertIn("post_processor", program.passthrough_data)

    def test_zne_path(self):
        """Test the ``prepare`` function when PEC is requested."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.resilience.zne_mitigation = True

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [(circuit, observable)]

        program, executor_options = prepare(pubs, options, precision=0.1)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        self.assertIn("qiskit_mitigation", program.passthrough_data)
        self.assertIn("post_processor", program.passthrough_data)

    def test_pea_path(self):
        """Test the ``prepare`` function when PEA is requested."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.resilience.zne_mitigation = True
        options.resilience.zne.amplifier = "pea"
        options.resilience.layer_noise_model = []

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [(circuit, observable)]

        program, executor_options = prepare(pubs, options, precision=0.1)

        self.assertIsInstance(program, QuantumProgram)
        self.assertIsInstance(executor_options, ExecutorOptions)
        self.assertIn("qiskit_mitigation", program.passthrough_data)
        self.assertIn("post_processor", program.passthrough_data)

    def test_pub_with_boxes_raises(self):
        """Test that a when a PUB contains a box, the estimator raises."""
        circuit = QuantumCircuit(2)
        with circuit.box():
            circuit.noop(0)
        circuit.measure_all()

        observable = "ZZ"

        pubs = [(circuit, observable)]
        with self.assertRaisesRegex(IBMInputValueError, "not supported"):
            prepare(pubs=pubs, options=EstimatorOptions(), precision=0.1)

    @data(True, False)
    def test_dd_applied_when_enabled(self, twirling_enabled):
        """Test apply_dynamical_decoupling is called when DD is enabled.

        Tests with twirling enabled and disabled (samplex item vs circuit item).
        """
        options = EstimatorOptions()
        options.dynamical_decoupling.enable = True
        options.twirling.enable_gates = twirling_enabled
        options.twirling.enable_measure = False
        options.resilience.measure_mitigation = False

        # Create a circuit with a large delay on qubit 0.
        circuit = QuantumCircuit(3)
        for _ in range(10):
            circuit.cx(1, 2)
        circuit.cx(0, 1)
        observable = SparsePauliOp.from_list([("ZZZ", 1)])

        pubs = [(circuit, observable), (circuit, observable)]

        program, _ = prepare(pubs, options, precision=0.1, backend=FakeManilaV2())

        # DD inserts X gates into idle slots of each circuit item
        for item in program.items:
            self.assertIn("x", item.circuit.count_ops())

    def test_dd_rejects_dynamic_circuits(self):
        """Test DD raises an error for circuits with control flow."""
        options = EstimatorOptions()
        options.dynamical_decoupling.enable = True

        circuit = QuantumCircuit(2, 1)
        circuit.h(0)
        circuit.measure(0, 0)
        circuit.if_else((0, True), QuantumCircuit(2, 1), QuantumCircuit(2, 1), [0, 1], [0])

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pubs = [(circuit, observable)]

        with self.assertRaisesRegex(
            IBMInputValueError,
            "Dynamical decoupling is not compatible with dynamic circuits",
        ):
            prepare(pubs, options, precision=0.1, backend=FakeManilaV2())

    def test_dd_raises_when_no_backend(self):
        """Test DD raises an error when no backend is provided."""
        options = EstimatorOptions()
        options.dynamical_decoupling.enable = True

        circuit = QuantumCircuit(2)
        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pubs = [(circuit, observable)]

        with self.assertRaisesRegex(
            IBMInputValueError,
            "A backend must be provided when dynamical decoupling is enabled",
        ):
            prepare(pubs, options, precision=0.1)

    def test_measure_mitigation_rejects_projection_operators(self):
        """Test measurement mitigation raises when observables contain projectors."""
        options = EstimatorOptions()
        options.resilience.measure_mitigation = True

        circuit = QuantumCircuit(3)
        pubs = [(circuit, "Z0Z")]

        with self.assertRaisesRegex(
            IBMInputValueError,
            "Measurement mitigation is currently not supported when observables contain projection",
        ):
            prepare(pubs, options, precision=0.1)

    @data("pauli", "balanced_pauli", "local_c1", "local_pauli")
    def test_circuit_with_parametric_rzz_and_twirling(self, group):
        """Test the ``prepare`` function for PUBs that contain parametric RZZ gates.

        ``prepare`` should not raise when ``group`` is ``"local_pauli``.
        """
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.twirling.group = group

        circuit = QuantumCircuit(2)
        circuit.rzz(Parameter("theta"), 0, 1)
        params = np.random.random((1,))
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        pubs = [(circuit, observable, params)]

        if group in {"pauli", "balanced_pauli", "local_c1"}:
            with self.assertRaisesRegex(BuildError, "GroupMode LOCAL_PAULI"):
                prepare(pubs, options)
        else:
            prepare(pubs, options)


@ddt
class TestPrepareVanilla(IBMEstimatorPrepareTestCase):
    """Tests for the vanilla prepare path (no mitigation)."""

    def _prepare_vanilla(
        self,
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
        options = EstimatorOptions()
        options.twirling = twirling_options
        if measure_noise_learning is not None:
            options.resilience.measure_mitigation = True
            options.resilience.measure_noise_learning = measure_noise_learning
        else:
            options.resilience.measure_mitigation = False
        options.resilience.zne_mitigation = False
        options.resilience.pec_mitigation = False
        options.default_shots = shots
        quantum_program, _ = prepare(pubs, options, precision=None, add_tags=add_tags)
        return quantum_program

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

                program = self._prepare_vanilla(
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
                program = self._prepare_vanilla(
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
        program = self._prepare_vanilla(
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
        program = self._prepare_vanilla(pubs=[pub], twirling_options=twirling_options, shots=1024)

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
            self._prepare_vanilla([pub], twirling_options, 1024)

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

        program = self._prepare_vanilla(
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
                program = self._prepare_vanilla(
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


@ddt
class TestPreparePec(IBMEstimatorPrepareTestCase):
    """Tests for the PEC prepare path."""

    def _prepare_pec(
        self,
        pubs: Iterable[EstimatorPubLike],
        twirling_options: TwirlingOptions,
        shots: int,
        pec_options: PecOptions,
        noise_model: dict,
        measure_noise_learning: MeasureNoiseLearningOptions | None = None,
        add_tags: bool = False,
    ) -> QuantumProgram:
        """Drop-in for the old ``prepare_pec`` that delegates to ``prepare()``.

        ``noise_model`` is ``dict[ref, PauliLindbladMap]``.  We rebuild the
        ``(CircuitInstruction, PauliLindbladMap)`` pairs that ``layer_noise_model``
        expects by calling ``find_unique_layers`` with the same twirling options.
        """
        options = EstimatorOptions()
        options.twirling = twirling_options
        options.resilience.pec_mitigation = True
        options.resilience.pec = pec_options
        options.resilience.measure_mitigation = measure_noise_learning is not None
        if measure_noise_learning is not None:
            options.resilience.measure_noise_learning = measure_noise_learning
        options.default_shots = shots

        all_pubs = [EstimatorPub.coerce(p) if not isinstance(p, EstimatorPub) else p for p in pubs]
        if noise_model:
            layers = find_unique_layers(all_pubs, twirling_options, inject_noise=True)
            options.resilience.layer_noise_model = [
                (layer, noise_model[get_annotation(layer.operation, InjectNoise).ref])
                for layer in layers
                if get_annotation(layer.operation, InjectNoise) is not None
                and get_annotation(layer.operation, InjectNoise).ref in noise_model
            ]
        else:
            options.resilience.layer_noise_model = []

        quantum_program, _ = prepare(pubs, options, precision=None, add_tags=add_tags)
        return quantum_program

    @data([True, True], [True, False])
    @unpack
    def test_param_basis_expansion_3q(self, enable_measure, enable_measure_noise_learning):
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
        twirling_options.enable_gates = True
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

                program = self._prepare_pec(
                    pubs=pubs,
                    twirling_options=twirling_options,
                    shots=10,
                    pec_options=PecOptions(),
                    noise_model={},
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

    @data([True, False], [True, True])
    @unpack
    def test_samplex_arguments_structure(self, enable_measure, enable_measure_noise_learning):
        """Test that samplex arguments have the expected structure for each circuit type."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        # Build a noise model mapping covering the layers of all scenario pubs.
        pubs = [scenario.pub for scenario in SAMPLEX_CIRCUIT_SCENARIOS]
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        noise_model = {
            annot.ref: PauliLindbladMap.from_sparse_list(
                [("Z" * len(layer.qubits), list(range(len(layer.qubits))), 0.1)],
                num_qubits=len(layer.qubits),
            )
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

        for scenario in SAMPLEX_CIRCUIT_SCENARIOS:
            with self.subTest(circuit=scenario.label):
                program = self._prepare_pec(
                    pubs=[scenario.pub],
                    twirling_options=twirling_options,
                    shots=10,
                    pec_options=PecOptions(),
                    noise_model=noise_model,
                    measure_noise_learning=measure_noise_learning,
                )
                # PEC always requires enable_gates=True
                self.assertSamplexArgumentsAreCorrect(program.items[0], scenario, inject_noise=True)

    def test_template_circuit(self):
        """Test that the template circuit has the expected clbits and parameter count."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        scenario = TEMPLATE_CIRCUIT_SCENARIO
        pubs = [scenario.pub]
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        noise_model = {
            annot.ref: PauliLindbladMap.from_sparse_list(
                [("Z" * len(layer.qubits), list(range(len(layer.qubits))), 0.1)],
                num_qubits=len(layer.qubits),
            )
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

        program = self._prepare_pec(
            pubs=pubs,
            twirling_options=twirling_options,
            shots=10,
            pec_options=PecOptions(),
            noise_model=noise_model,
        )
        self.assertTemplateCircuitIsCorrect(program.items[0], scenario, enable_gates=True)

    def test_prepare_pec_basic(self):
        """Test prepare_pec with basic PEC options and noise model."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list(
            [("XX", [0, 1], 0.1), ("ZZ", [0, 1], 0.05)], num_qubits=2
        )
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = self._prepare_pec(
            [pub], twirling_options, shots, pec_options, noise_model
        )

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, 64)
        self.assertEqual(len(quantum_program.items), 1)

        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIsInstance(item, SamplexItem)

        # Check that samplex_arguments contains pauli_lindblad_maps
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_ref}"],
            noise_model[noise_layer_ref],
        )

        # Check that samplex_arguments contains noise_scales for the layer
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        # noise_gain = 0.5, so noise_scale = noise_gain - 1 = -0.5
        expected_noise_factor = pec_options.noise_gain - 1
        self.assertEqual(
            item.samplex_arguments[f"noise_scales.{noise_layer_ref}"], expected_noise_factor
        )

        # check number of randomizations
        expected_gamma = float(np.exp(2 * pec_options.noise_gain * (0.1 + 0.05)))
        overhead = expected_gamma**2
        expected_num_rands = math.ceil(overhead * (shots / 64))
        self.assertEqual(item.shape[0], expected_num_rands)

    def test_prepare_pec_with_auto_noise_gain(self):
        """Test prepare_pec with auto noise_gain (defaults to 0)."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        err_rate = 0.7
        max_overhead = 10
        noise_model = PauliLindbladMap.from_sparse_list([("IX", [0, 1], err_rate)], num_qubits=2)
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = "auto"
        pec_options.max_overhead = max_overhead

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = self._prepare_pec(
            [pub], twirling_options, shots, pec_options, noise_model
        )

        item = cast("SamplexItem", quantum_program.items[0])

        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        scaleless_gamma = float(np.exp(2 * err_rate))
        expected_noise_gain = -np.log(max_overhead) / np.log(scaleless_gamma**2)
        self.assertEqual(
            item.samplex_arguments[f"noise_scales.{noise_layer_ref}"], expected_noise_gain
        )

    def test_prepare_pec_raises_error_with_empty_noise_model(self):
        """Test that prepare_pec raises error when noise_model is empty."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaisesRegex(ValueError, "Noise model is missing"):
            self._prepare_pec([pub], twirling_options, 1024, pec_options, {})

    def test_prepare_pec_raises_error_with_missing_noise_model_key(self):
        """Test that prepare_pec raises error when noise_model is missing a noise model."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(2)
        circuit2.h(0)
        circuit2.cz(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub1 = EstimatorPub.coerce((circuit1, observable))
        pub2 = EstimatorPub.coerce((circuit2, observable))

        # Only provide noise model for one pub, but we have two pubs
        noise_model = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        layers = find_unique_layers([pub1], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaisesRegex(ValueError, "Noise model is missing"):
            self._prepare_pec([pub1, pub2], twirling_options, 1024, pec_options, noise_model)

    def test_prepare_pec_warns_when_measurement_twirling_is_false(self):
        """Test that prepare_pec raises warns when measurement twirling is set to ``False``."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list(
            [("XX", [0, 1], 0.1), ("ZZ", [0, 1], 0.05)], num_qubits=2
        )
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = False

        with self.assertWarnsRegex(UserWarning, "twirling.enable_measure"):
            self._prepare_pec([pub], twirling_options, 10, pec_options, noise_model)

    @data(32, "auto")
    def test_prepare_pec_with_measure_noise_learning(self, num_randomizations):
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

        noise_model = self._build_trivial_noise_model(pubs, twirling_options)

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = num_randomizations

        program = self._prepare_pec(
            pubs, twirling_options, 1024, PecOptions(), noise_model, measure_noise_learning
        )

        # 2 pubs + 1 TREX calibration item.
        self.assertEqual(len(program.items), 3)
        expected_trex_randomizations = (
            twirling_options.num_randomizations
            if num_randomizations == "auto"
            else num_randomizations
        )
        self.assertTrexItemIsCorrect(
            program, pubs, expected_num_randomizations=expected_trex_randomizations
        )

    def test_prepare_pec_with_trivial_noise_maps(self):
        """Test ``prepare_pec`` with noise maps set to identity."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        # Create a simple noise model
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref
        noise_model = {noise_layer_ref: PauliLindbladMap.identity(num_qubits=2)}

        pec_options = PecOptions()
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = self._prepare_pec(
            [pub], twirling_options, shots, pec_options, noise_model
        )
        item = cast("SamplexItem", quantum_program.items[0])
        self.assertEqual(item.samplex_arguments[f"noise_scales.{noise_layer_ref}"], 0)

    def test_prepare_pec_identical_pubs_have_same_num_randomizations(self):
        """Test that identical pubs produce the same number of randomizations.

        Regression test for a bug where ``num_randomizations`` was overwritten
        inside the per-pub loop, causing each subsequent pub to compound the
        previous pub's gamma-scaled value instead of starting from the baseline.
        """
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list(
            [("XX", [0, 1], 0.1), ("ZZ", [0, 1], 0.05)], num_qubits=2
        )
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = next(
            annot.ref for layer in layers if (annot := get_annotation(layer.operation, InjectNoise))
        )
        noise_model = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        quantum_program = self._prepare_pec(
            [pub, pub], twirling_options, 1024, pec_options, noise_model
        )

        item0 = cast("SamplexItem", quantum_program.items[0])
        item1 = cast("SamplexItem", quantum_program.items[1])
        self.assertEqual(
            item0.shape[0],
            item1.shape[0],
        )

    def _build_trivial_noise_model(self, pubs, twirling_options):
        """Build a trivial (zero-rate) noise model mapping for the given PUBs."""
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        return {
            annot.ref: PauliLindbladMap.from_sparse_list([], num_qubits=len(layer.qubits))
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

    def test_shapes_twirling_configs(self):
        """Verify the number of randomizations and program.shots."""
        pec_options = PecOptions()
        pec_options.noise_gain = 1.0  # no noise removal → gamma=1, no randomization overhead

        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        pub = EstimatorPub.coerce((qc, SparsePauliOp.from_list([("ZZ", 1)])))

        for scenario in TWIRLING_SHAPE_SCENARIOS:
            if not scenario.twirling_options.enable_gates:
                continue  # PEC requires enable_gates=True
            with self.subTest(twirling=scenario.label):
                noise_model = self._build_trivial_noise_model([pub], scenario.twirling_options)
                program = self._prepare_pec(
                    pubs=[pub],
                    twirling_options=scenario.twirling_options,
                    shots=scenario.shots,
                    pec_options=pec_options,
                    noise_model=noise_model,
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

    def test_shapes_overhead_scaling(self):
        """PEC overhead: num randomizations exceeds baseline when gamma > 1.

        Uses a non-trivial noise model with a known error rate so that gamma > 1 and
        the scaled num_randomizations exceeds the baseline.
        """
        pec_options = PecOptions()
        # noise_gain=0 means full PEC (maximum overhead scaling)
        pec_options.noise_gain = 0.0

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        pub = EstimatorPub.coerce((qc, SparsePauliOp.from_list([("ZZ", 1)])))

        # Build a non-trivial noise model with a meaningful error rate
        layers = find_unique_layers([pub], twirling_options, inject_noise=True)
        noise_model = {
            annot.ref: PauliLindbladMap.from_sparse_list(
                [("ZZ", [0, 1], 0.1)], num_qubits=len(layer.qubits)
            )
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

        shots = 1024
        program = self._prepare_pec(
            pubs=[pub],
            twirling_options=twirling_options,
            shots=shots,
            pec_options=pec_options,
            noise_model=noise_model,
        )

        baseline_num_rand, _ = calculate_twirling_shots(shots, "auto", "auto")
        item = program.items[0]
        self.assertGreater(
            item.shape[0],
            baseline_num_rand,
            msg=f"Expected overhead-scaled R > baseline R={baseline_num_rand}, got {item.shape[0]}",
        )


@ddt
class TestPrepareZne(IBMEstimatorPrepareTestCase):
    """Tests for the ZNE prepare path."""

    def _prepare_zne(
        self,
        pubs: Iterable[EstimatorPubLike],
        twirling_options: TwirlingOptions,
        shots: int,
        zne_options: ZneOptions,
        measure_noise_learning: MeasureNoiseLearningOptions | None = None,
        add_tags: bool = False,
    ) -> QuantumProgram:
        """Drop-in for the old ``prepare_zne`` that delegates to ``prepare()``."""
        options = EstimatorOptions()
        options.twirling = twirling_options
        options.resilience.zne_mitigation = True
        options.resilience.zne = zne_options
        options.resilience.measure_mitigation = measure_noise_learning is not None
        if measure_noise_learning is not None:
            options.resilience.measure_noise_learning = measure_noise_learning
        options.default_shots = shots
        quantum_program, _ = prepare(pubs, options, precision=None, add_tags=add_tags)
        return quantum_program

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

                program = self._prepare_zne(
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
                program = self._prepare_zne(
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
        program = self._prepare_zne(
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
        quantum_program = self._prepare_zne([pub], TwirlingOptions(), shots, zne_options)

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
        quantum_program = self._prepare_zne([pub], TwirlingOptions(), shots, zne_options)

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

        program = self._prepare_zne(
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
            self._prepare_zne([pub], twirling_options, 100, zne_options)

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
                program = self._prepare_zne(
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


@ddt
class TestPreparePea(IBMEstimatorPrepareTestCase):
    """Tests for the PEA prepare path."""

    def _prepare_pea(
        self,
        pubs: Iterable[EstimatorPubLike],
        twirling_options: TwirlingOptions,
        shots: int,
        zne_options: ZneOptions,
        noise_model: dict,
        measure_noise_learning: MeasureNoiseLearningOptions | None = None,
        add_tags: bool = False,
    ) -> QuantumProgram:
        """Drop-in for the old ``prepare_pea`` that delegates to ``prepare()``.

        ``noise_model`` is ``dict[ref, PauliLindbladMap]``.  We rebuild the
        ``(CircuitInstruction, PauliLindbladMap)`` pairs that ``layer_noise_model``
        expects by calling ``find_unique_layers`` with the same twirling options.
        """
        options = EstimatorOptions()
        options.twirling = twirling_options
        options.resilience.zne_mitigation = True
        options.resilience.zne = zne_options
        options.resilience.measure_mitigation = measure_noise_learning is not None
        if measure_noise_learning is not None:
            options.resilience.measure_noise_learning = measure_noise_learning
        options.default_shots = shots

        all_pubs = [EstimatorPub.coerce(p) if not isinstance(p, EstimatorPub) else p for p in pubs]
        if noise_model:
            layers = find_unique_layers(all_pubs, twirling_options, inject_noise=True)
            options.resilience.layer_noise_model = [
                (layer, noise_model[get_annotation(layer.operation, InjectNoise).ref])
                for layer in layers
                if get_annotation(layer.operation, InjectNoise) is not None
                and get_annotation(layer.operation, InjectNoise).ref in noise_model
            ]
        else:
            options.resilience.layer_noise_model = []

        quantum_program, _ = prepare(pubs, options, precision=None, add_tags=add_tags)
        return quantum_program

    @data([True, True], [True, False])
    @unpack
    def test_param_basis_expansion_3q(self, enable_measure, enable_measure_noise_learning):
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
        twirling_options.enable_gates = True
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1, 2, 3, 4]

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

                program = self._prepare_pea(
                    pubs=pubs,
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=zne_options,
                    noise_model={},
                    measure_noise_learning=measure_noise_learning,
                )

                # param_basis_pairs now lives in the qiskit_mitigation passthrough block.
                param_basis_pairs = program.passthrough_data["qiskit_mitigation"][0][
                    "param_basis_pairs"
                ]

                # Check that the param-basis pairs are the correct ones
                self.assertListEqual(param_basis_pairs, expected_pairs, msg=param_basis_pairs)

                # Check that the quantum program has one element per param-basis pair
                self.assertEqual(
                    program.items[0].shape,
                    (len(zne_options.noise_factors), 1, len(expected_pairs)),
                )

    @data([True, False], [True, True])
    @unpack
    def test_samplex_arguments_structure(self, enable_measure, enable_measure_noise_learning):
        """Test that samplex arguments have the expected structure for each circuit type."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1, 2, 3]

        # Build a noise model mapping covering the layers of all scenario pubs.
        pubs = [scenario.pub for scenario in SAMPLEX_CIRCUIT_SCENARIOS]
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        noise_model = {
            annot.ref: PauliLindbladMap.from_sparse_list(
                [("Z" * len(layer.qubits), list(range(len(layer.qubits))), 0.1)],
                num_qubits=len(layer.qubits),
            )
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

        for scenario in SAMPLEX_CIRCUIT_SCENARIOS:
            with self.subTest(circuit=scenario.label):
                program = self._prepare_pea(
                    pubs=[scenario.pub],
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=zne_options,
                    noise_model=noise_model,
                    measure_noise_learning=measure_noise_learning,
                )
                # PEA always requires enable_gates=True
                self.assertSamplexArgumentsAreCorrect(program.items[0], scenario, inject_noise=True)

    def test_template_circuit(self):
        """Test that the template circuit has the expected clbits and parameter count."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1, 2, 3]

        scenario = TEMPLATE_CIRCUIT_SCENARIO
        pubs = [scenario.pub]
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        noise_model = {
            annot.ref: PauliLindbladMap.from_sparse_list(
                [("Z" * len(layer.qubits), list(range(len(layer.qubits))), 0.1)],
                num_qubits=len(layer.qubits),
            )
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

        program = self._prepare_pea(
            pubs=pubs,
            twirling_options=twirling_options,
            shots=10,
            zne_options=zne_options,
            noise_model=noise_model,
        )
        self.assertTemplateCircuitIsCorrect(program.items[0], scenario, enable_gates=True)

    def test_prepare_pea_basic(self):
        """Test prepare_pea with basic noise factors and noise model."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list(
            [("XX", [0, 1], 0.1), ("ZZ", [0, 1], 0.05)], num_qubits=2
        )
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model = {noise_layer_ref: noise_model}

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = self._prepare_pea(
            [pub], twirling_options, shots, zne_options, noise_model
        )

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, 64)
        self.assertEqual(len(quantum_program.items), 1)

        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIsInstance(item, SamplexItem)
        # Check samplex shape
        auto_num_rand = math.ceil(shots / (max(64, math.ceil(shots / 32))))
        # The expected shape is (num_noise_factors, num_randomizations, bases * num_param_sets)
        expected_shape = (len(noise_factors), auto_num_rand, 1)
        self.assertEqual(item.shape, expected_shape)

        # Check that samplex_arguments contains pauli_lindblad_maps
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_ref}"],
            noise_model[noise_layer_ref],
        )

        # Check that samplex_arguments contains noise_scales for the layer
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        # noise_scales = noise_factors - 1, shape is (num_noise_factors, 1, 1)
        expected_noise_scales = np.array([[[factor - 1]] for factor in noise_factors])
        self.assertTrue(
            np.all(
                item.samplex_arguments[f"noise_scales.{noise_layer_ref}"] == expected_noise_scales
            )
        )

    def test_prepare_pea_raises_error_with_empty_noise_model(self):
        """Test that prepare_pea raises error when noise_model is empty."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaisesRegex(ValueError, "Noise model is missing"):
            self._prepare_pea([pub], twirling_options, 1024, zne_options, {})

    def test_prepare_pea_raises_error_with_missing_noise_model_key(self):
        """Test that prepare_pea raises error when noise_model is missing a noise model."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(2)
        circuit2.h(0)
        circuit2.cz(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub1 = EstimatorPub.coerce((circuit1, observable))
        pub2 = EstimatorPub.coerce((circuit2, observable))

        # Only provide noise model for one pub, but we have two pubs
        noise_model = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        layers = find_unique_layers([pub1], TwirlingOptions(), inject_noise=True)
        noise_layer_ref_pub1 = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref_pub1 = annot.ref

        noise_model = {noise_layer_ref_pub1: noise_model}

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaisesRegex(ValueError, "Noise model is missing"):
            self._prepare_pea([pub1, pub2], twirling_options, 1024, zne_options, noise_model)

    def test_prepare_pea_warns_when_measurement_twirling_is_false(self):
        """Test that prepare_pea raises warns when measurement twirling is set to ``False``."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list(
            [("XX", [0, 1], 0.1), ("ZZ", [0, 1], 0.05)], num_qubits=2
        )
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model = {noise_layer_ref: noise_model}

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = False

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"

        with self.assertWarnsRegex(UserWarning, "twirling.enable_measure"):
            self._prepare_pea([pub], twirling_options, 10, zne_options, noise_model)

    @data(32, "auto")
    def test_prepare_pea_with_measure_noise_learning(self, num_randomizations):
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

        noise_model = self._build_trivial_noise_model(pubs, twirling_options)

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1.0, 2.0]

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = num_randomizations

        program = self._prepare_pea(
            pubs, twirling_options, 1024, zne_options, noise_model, measure_noise_learning
        )

        # 2 pubs + 1 TREX calibration item.
        self.assertEqual(len(program.items), 3)
        expected_trex_randomizations = (
            twirling_options.num_randomizations
            if num_randomizations == "auto"
            else num_randomizations
        )
        self.assertTrexItemIsCorrect(
            program, pubs, expected_num_randomizations=expected_trex_randomizations
        )

    def test_prepare_pea_raises_error_with_less_than_2_noise_factors(self):
        """Test that prepare_pea raises when noise_factors has less than 2 points."""
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        with self.assertRaisesRegex(ValueError, "Must have at least two noise factors"):
            zne_options.noise_factors = [1.5]

    def test_prepare_pea_raises_error_with_too_few_noise_factors_for_extrapolator(self):
        """Test that prepare_pea rejects noise_factors under-specified for the extrapolator."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.extrapolator = "double_exponential"
        zne_options.noise_factors = [1.0, 3.0]

        with self.assertRaisesRegex(
            IBMInputValueError, "double_exponential requires at least 4 noise_factors"
        ):
            self._prepare_pea(
                [pub], twirling_options, shots=100, zne_options=zne_options, noise_model={}
            )

    def _build_trivial_noise_model(self, pubs, twirling_options):
        """Build a trivial (zero-rate) noise model mapping for the given PUBs."""
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        return {
            annot.ref: PauliLindbladMap.from_sparse_list([], num_qubits=len(layer.qubits))
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

    def test_shapes_twirling_configs(self):
        """Verify the number of randomizations and program.shots.

        PEA shape is (num_noise_factors, num_randomizations, num_basis).
        """
        noise_factors = [1.0, 3.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        pub = EstimatorPub.coerce((qc, SparsePauliOp.from_list([("ZZ", 1)])))

        for scenario in TWIRLING_SHAPE_SCENARIOS:
            if not scenario.twirling_options.enable_gates:
                continue  # PEA requires enable_gates=True
            with self.subTest(twirling=scenario.label):
                noise_model = self._build_trivial_noise_model([pub], scenario.twirling_options)
                program = self._prepare_pea(
                    pubs=[pub],
                    twirling_options=scenario.twirling_options,
                    shots=scenario.shots,
                    zne_options=zne_options,
                    noise_model=noise_model,
                )
                item = program.items[0]
                self.assertEqual(
                    item.shape[0],
                    len(noise_factors),
                    msg=f"[{scenario.label}] expected N={len(noise_factors)}, got {item.shape[0]}",
                )
                self.assertEqual(
                    item.shape[1],
                    scenario.expected_num_randomizations,
                    msg=f"[{scenario.label}] expected R={scenario.expected_num_randomizations}, "
                    f"got {item.shape[1]}",
                )
                self.assertEqual(
                    program.shots,
                    scenario.expected_shots_per_randomization,
                    msg=f"[{scenario.label}] expected program.shots="
                    f"{scenario.expected_shots_per_randomization}, got {program.shots}",
                )
