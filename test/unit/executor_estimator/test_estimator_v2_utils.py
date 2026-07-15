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

"""Unit tests for EstimatorV2 helper functions."""

import unittest

import numpy as np
from ddt import data, ddt
from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import Pauli, SparsePauliOp
from samplomatic import Tag
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.utils import (
    box_circuit,
    compute_samplex_arguments,
    get_pauli_basis,
    pauli_to_ints,
    resolve_precision,
)


class TestComputeSamplexArguments(unittest.TestCase):
    """Tests for compute_samplex_arguments function."""

    def test_binding_array_key_order_bound_by_circuit_parameters(self):
        """Parameter values must be ordered by ``circuit.parameters``.

        Regression: ``compute_samplex_arguments`` used to call ``as_array()``
        without passing the circuit's parameters, so a dict/BindingsArray whose
        key order differed from ``circuit.parameters`` bound values to the wrong
        parameters silently.
        """
        a = Parameter("a")
        b = Parameter("b")
        circuit = QuantumCircuit(1)
        circuit.rx(a, 0)
        circuit.rz(b, 0)
        # circuit.parameters is canonically sorted -> (a, b).
        self.assertEqual([p.name for p in circuit.parameters], ["a", "b"])

        # Key the bindings in the opposite order (b, a); intended a=0.1, b=0.7.
        pub = EstimatorPub.coerce((circuit, SparsePauliOp("Z"), {("b", "a"): [0.7, 0.1]}))

        flat_parameter_values, _, _ = compute_samplex_arguments(pub)

        # A single observable term "Z" -> one measurement basis -> one flattened
        # row, ordered by circuit.parameters (a, b), not by the dict key order (b, a).
        np.testing.assert_array_equal(flat_parameter_values, [[0.1, 0.7]])


class TestGetPauliBasis(unittest.TestCase):
    """Tests for get_pauli_basis function."""

    def test_single_qubit_bases(self):
        """Test single-qubit basis conversions."""
        for basis, expected in [
            ("0", Pauli("Z")),
            ("1", Pauli("Z")),
            ("+", Pauli("X")),
            ("-", Pauli("X")),
            ("r", Pauli("Y")),
            ("l", Pauli("Y")),
            ("I", Pauli("I")),
        ]:
            with self.subTest(basis=basis):
                result = get_pauli_basis(basis)
                self.assertEqual(result, expected)

    def test_multi_qubit(self):
        """Test multi-qubit basis conversion."""
        result = get_pauli_basis("0+r")
        expected = Pauli("ZXY")
        self.assertEqual(result, expected)


class TestPauliToInts(unittest.TestCase):
    """Tests for pauli_to_ints function."""

    def test_single_qubit_paulis(self):
        """Test single-qubit Pauli to integer conversions."""
        for pauli, expected in [
            (Pauli("I"), [0]),
            (Pauli("Z"), [1]),
            (Pauli("X"), [2]),
            (Pauli("Y"), [3]),
        ]:
            with self.subTest(pauli=str(pauli)):
                result = pauli_to_ints(pauli)
                self.assertEqual(result, expected)

    def test_multi_qubit(self):
        """Test multi-qubit Pauli conversion."""
        result = pauli_to_ints(Pauli("IZXY"))
        self.assertEqual(result, [3, 2, 1, 0])


class TestResolvePrecision(unittest.TestCase):
    """Tests for resolve_precision function."""

    def setUp(self):
        """Set up test fixtures."""
        self.circuit = QuantumCircuit(2)
        self.circuit.h(0)
        self.observable = SparsePauliOp.from_list([("ZZ", 1)])

    def test_all_pubs_with_same_precision(self):
        """Test when all pubs have the same precision value."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        pub3 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)

        result = resolve_precision([pub1, pub2, pub3])
        self.assertEqual(result, 0.01)

    def test_all_pubs_without_precision_with_run_precision(self):
        """Test when no pubs have precision but run_precision is provided."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable))
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))
        pub3 = EstimatorPub.coerce((self.circuit, self.observable))

        result = resolve_precision([pub1, pub2, pub3], run_precision=0.02)
        self.assertEqual(result, 0.02)

    def test_all_pubs_without_precision_no_run_precision(self):
        """Test when no pubs have precision and no run_precision is provided."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable))
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))

        result = resolve_precision([pub1, pub2])
        self.assertIsNone(result)

    def test_mixture_some_with_precision_some_without_matching_run_precision(self):
        """Test mixture where all pubs resolve to same value."""
        # Pubs with explicit precision
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        # Pubs without precision (will use run_precision)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))
        pub3 = EstimatorPub.coerce((self.circuit, self.observable))

        # run_precision matches the explicit precision
        result = resolve_precision([pub1, pub2, pub3], run_precision=0.01)
        self.assertEqual(result, 0.01)

    def test_mixture_some_with_precision_some_without_mismatched_run_precision(self):
        """Test mixture where pubs have different precision values (explicit vs run_precision)."""
        # Pub with explicit precision
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        # Pubs without precision (will use run_precision which is different)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable))
        pub3 = EstimatorPub.coerce((self.circuit, self.observable))

        # run_precision is different from explicit precision
        with self.assertRaises(IBMInputValueError) as context:
            resolve_precision([pub1, pub2, pub3], run_precision=0.02)

        self.assertIn("same precision", str(context.exception))

    def test_mixture_multiple_different_explicit_precisions(self):
        """Test mixture where pubs have different explicit precision values."""
        pub1 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.01)
        pub2 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.02)
        pub3 = EstimatorPub.coerce((self.circuit, self.observable), precision=0.03)

        with self.assertRaises(IBMInputValueError) as context:
            resolve_precision([pub1, pub2, pub3])

        self.assertIn("same precision", str(context.exception))

    def test_pub_level_zero_precision_raises(self):
        """Test that a pub-level precision of 0 is rejected."""
        pub = EstimatorPub.coerce((self.circuit, self.observable), precision=0)

        with self.assertRaisesRegex(IBMInputValueError, "must be strictly greater than 0"):
            resolve_precision([pub])

    def test_run_level_zero_precision_raises(self):
        """Test that a run-level precision of 0 is rejected when pubs have no precision."""
        pub = EstimatorPub.coerce((self.circuit, self.observable))

        with self.assertRaisesRegex(IBMInputValueError, "must be strictly greater than 0"):
            resolve_precision([pub], run_precision=0)


@ddt
class TestBoxCircuit(unittest.TestCase):
    """Tests for ``box_circuit``."""

    @data(True, False)
    def test_enable_gates(self, enable_gates):
        """Tests for the ``enable_gates`` argument."""
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        circuit_out = box_circuit(
            circuit,
            enable_gates=enable_gates,
            measure_annotations="all",
            twirling_strategy="all",
            twirling_group="pauli",
        )

        pm = generate_boxing_pass_manager(
            enable_gates=enable_gates,
            measure_annotations="all",
            twirling_strategy="all",
            inject_noise_site="after",
            twirling_group="pauli",
        )

        expected_circuit = circuit.remove_final_measurements(inplace=False)
        expected_circuit.add_register(ClassicalRegister(expected_circuit.num_qubits, "_meas"))
        expected_circuit.measure(range(3), range(3))
        expected_circuit = pm.run(expected_circuit)

        self.assertEqual(circuit_out, expected_circuit)

    @data("change_basis", "all")
    def test_measure_annotations(self, measure_annotations):
        """Tests for the ``measure_annotations`` argument."""
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        circuit_out = box_circuit(
            circuit,
            enable_gates=True,
            measure_annotations=measure_annotations,
            twirling_strategy="all",
            twirling_group="pauli",
        )

        pm = generate_boxing_pass_manager(
            enable_gates=True,
            measure_annotations=measure_annotations,
            twirling_strategy="all",
            inject_noise_site="after",
            twirling_group="pauli",
        )

        expected_circuit = circuit.remove_final_measurements(inplace=False)
        expected_circuit.add_register(ClassicalRegister(expected_circuit.num_qubits, "_meas"))
        expected_circuit.measure(range(3), range(3))
        expected_circuit = pm.run(expected_circuit)

        self.assertEqual(circuit_out, expected_circuit)

    @data("active", "active_accum", "active_circuit", "all")
    def test_twirling_strategy(self, twirling_strategy):
        """Tests for the ``twirling_strategy`` argument."""
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        circuit_out = box_circuit(
            circuit,
            enable_gates=True,
            measure_annotations="all",
            twirling_strategy=twirling_strategy,
            twirling_group="pauli",
        )

        pm = generate_boxing_pass_manager(
            enable_gates=True,
            measure_annotations="all",
            twirling_strategy=twirling_strategy,
            inject_noise_site="after",
            twirling_group="pauli",
        )

        expected_circuit = circuit.remove_final_measurements(inplace=False)
        expected_circuit.add_register(ClassicalRegister(expected_circuit.num_qubits, "_meas"))
        expected_circuit.measure(range(3), range(3))
        expected_circuit = pm.run(expected_circuit)

        self.assertEqual(circuit_out, expected_circuit)

    @data(True, False)
    def test_inject_noise(self, inject_noise):
        """Tests for the ``inject_noise`` argument."""
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        circuit_out = box_circuit(
            circuit,
            enable_gates=True,
            measure_annotations="all",
            twirling_strategy="all",
            twirling_group="pauli",
            inject_noise=inject_noise,
        )

        pm = generate_boxing_pass_manager(
            enable_gates=True,
            measure_annotations="all",
            twirling_strategy="all",
            twirling_group="pauli",
            inject_noise_targets="gates" if inject_noise else "none",
            inject_noise_strategy="uniform_modification" if inject_noise else "no_modification",
            inject_noise_site="after",
        )

        expected_circuit = circuit.remove_final_measurements(inplace=False)
        expected_circuit.add_register(ClassicalRegister(expected_circuit.num_qubits, "_meas"))
        expected_circuit.measure(range(3), range(3))
        expected_circuit = pm.run(expected_circuit)

        self.assertEqual(circuit_out, expected_circuit)

    @data("none", "unique_box", "unique_instance", "noise_ref")
    def test_add_tags(self, add_tags):
        """Tests for the ``add_tags`` argument.

        Checks that the circuit produced by ``box_circuit`` matches the expected circuit
        produced by ``generate_boxing_pass_manager`` with the same ``add_tags`` value, and
        that boxes carry :class:`~samplomatic.Tag` annotations if and only if ``add_tags``
        is not ``"none"``.
        """
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.measure_all()

        circuit_out = box_circuit(
            circuit,
            enable_gates=True,
            measure_annotations="all",
            twirling_strategy="all",
            twirling_group="balanced_pauli",
            add_tags=add_tags,
        )

        pm = generate_boxing_pass_manager(
            enable_gates=True,
            measure_annotations="all",
            twirling_strategy="all",
            add_tags=add_tags,
            inject_noise_site="after",
        )

        expected_circuit = circuit.remove_final_measurements(inplace=False)
        expected_circuit.add_register(ClassicalRegister(expected_circuit.num_qubits, "_meas"))
        expected_circuit.barrier()
        expected_circuit.measure(range(3), range(3))
        expected_circuit = pm.run(expected_circuit)

        self.assertEqual(circuit_out, expected_circuit)

        # Verify Tag annotations on box instructions.
        # "noise_ref" only tags boxes that are paired with injected-noise boxes; without
        # inject_noise=True there are no such pairs, so no tags are produced.
        box_instructions = [instr for instr in circuit_out if instr.operation.name == "box"]
        tagged_boxes = [
            instr for instr in box_instructions if get_annotation(instr.operation, Tag) is not None
        ]
        if add_tags in ("none", "noise_ref"):
            self.assertEqual(
                len(tagged_boxes),
                0,
                msg=f"Expected no tagged boxes for add_tags={add_tags!r} (without inject_noise), "
                f"but found {len(tagged_boxes)}.",
            )
        else:
            self.assertGreater(
                len(tagged_boxes),
                0,
                msg=f"Expected at least one tagged box for add_tags={add_tags!r}, but found none.",
            )
