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

"""Tests for client-side Sampler utility functions."""

from ddt import data, ddt
from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.primitives.containers.sampler_pub import SamplerPub
from samplomatic import Tag
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_sampler.utils import box_circuit, extract_shots_from_pubs

from ...ibm_test_case import IBMBoxedCircuitTestCase, IBMTestCase


class TestExtractShotsFromPubs(IBMTestCase):
    """Tests for extract_shots_from_pubs function."""

    def test_single_pub_with_shots(self):
        """Test extracting shots from a single pub with shots specified."""
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        shots = extract_shots_from_pubs([pub])

        self.assertEqual(shots, 1024)

    def test_single_pub_with_default_shots(self):
        """Test extracting shots using default_shots when pub doesn't specify."""
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots specified
        shots = extract_shots_from_pubs([pub], default_shots=2048)

        self.assertEqual(shots, 2048)

    def test_multiple_pubs_same_shots(self):
        """Test extracting shots from multiple pubs with same shots value."""
        circuit1 = QuantumCircuit(2, 2)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(3, 3)
        circuit2.h([0, 1, 2])
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=1024),
            SamplerPub.coerce(circuit2, shots=1024),
        ]
        shots = extract_shots_from_pubs(pubs)

        self.assertEqual(shots, 1024)

    def test_multiple_pubs_mixed_shots_sources(self):
        """Test multiple pubs where some use default_shots and some specify shots."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(1, 1)
        circuit2.x(0)
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=512),
            SamplerPub.coerce(circuit2),  # Will use default_shots
        ]
        shots = extract_shots_from_pubs(pubs, default_shots=512)

        self.assertEqual(shots, 512)

    def test_mismatched_shots_raises_error(self):
        """Test that mismatched shots across pubs raises an error."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(1, 1)
        circuit2.x(0)
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=1024),
            SamplerPub.coerce(circuit2, shots=2048),
        ]

        with self.assertRaises(IBMInputValueError) as context:
            extract_shots_from_pubs(pubs)

        self.assertIn("same number of shots", str(context.exception))
        self.assertIn("1024", str(context.exception))
        self.assertIn("2048", str(context.exception))

    def test_no_shots_specified_raises_error(self):
        """Test that missing shots raises an error."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots

        with self.assertRaises(IBMInputValueError) as context:
            extract_shots_from_pubs([pub], default_shots=None)

        self.assertIn("Shots must be specified", str(context.exception))

    def test_pub_shots_overrides_default(self):
        """Test that pub.shots takes precedence over default_shots."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        shots = extract_shots_from_pubs([pub], default_shots=2048)

        # Should use pub.shots (1024), not default_shots (2048)
        self.assertEqual(shots, 1024)

    def test_empty_pubs_returns_default_shots(self):
        """Test that empty pubs list returns default_shots."""
        shots = extract_shots_from_pubs([], default_shots=4096)

        self.assertEqual(shots, 4096)


@ddt
class TestBoxCircuit(IBMBoxedCircuitTestCase):
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

        self.assertCircuitsAnnotationsAreEqual(circuit_out, expected_circuit)
        self.assertCircuitsEqualIgnoringAnnotations(circuit_out, expected_circuit)

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

        self.assertCircuitsEqualIgnoringAnnotations(circuit_out, expected_circuit)
        self.assertCircuitsAnnotationsAreEqual(circuit_out, expected_circuit)

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

        self.assertCircuitsAnnotationsAreEqual(circuit_out, expected_circuit)
        self.assertCircuitsEqualIgnoringAnnotations(circuit_out, expected_circuit)

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

        self.assertCircuitsAnnotationsAreEqual(circuit_out, expected_circuit)
        self.assertCircuitsEqualIgnoringAnnotations(circuit_out, expected_circuit)

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
            twirling_group="balanced_pauli",
            add_tags=add_tags,
            inject_noise_site="after",
        )

        expected_circuit = circuit.remove_final_measurements(inplace=False)
        expected_circuit.add_register(ClassicalRegister(expected_circuit.num_qubits, "_meas"))
        expected_circuit.barrier()
        expected_circuit.measure(range(3), range(3))
        expected_circuit = pm.run(expected_circuit)

        self.assertCircuitsEqualIgnoringAnnotations(circuit_out, expected_circuit)
        self.assertCircuitsAnnotationsAreEqual(circuit_out, expected_circuit)

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
