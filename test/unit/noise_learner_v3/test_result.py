# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests the classes `NoiseLearnerV3Result` and `NoiseLearnerV3Results`."""

import numpy as np
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap, QubitSparsePauliList
from samplomatic import InjectNoise, Tag, Twirl

from qiskit_ibm_runtime.results.noise_learner_v3 import NoiseLearnerV3Result, NoiseLearnerV3Results

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3Result(IBMTestCase):
    """Tests the ``NoiseLearnerV3Result`` class."""

    def test_from_generators_valid_input(self):
        """Test ``NoiseLearnerV3Result.from_generators``."""
        generators = [
            QubitSparsePauliList.from_label(pauli1 + pauli0)
            for pauli1 in "IXYZ"
            for pauli0 in "IXYZ"
        ][1:]
        rates = np.arange(0, 0.3, 0.02)
        rates_std = np.arange(0, 0.15, 0.01)
        metadata = {"learning_protocol": "lindblad"}
        result = NoiseLearnerV3Result.from_generators(generators, rates, rates_std, metadata)
        self.assertEqual(generators, result._generators)
        self.assertTrue(np.array_equal(np.array(rates), result._rates))
        self.assertTrue(np.array_equal(rates_std, result._rates_std))
        self.assertEqual(metadata, result.metadata)
        self.assertEqual(len(result), 15)

    def test_from_generators_different_lengths(self):
        """Test ``.from_generators`` raises if the generators and rates have different lengths."""
        generators = [
            QubitSparsePauliList.from_label(pauli1 + pauli0)
            for pauli1 in "IXYZ"
            for pauli0 in "IXYZ"
        ][1:]
        rates = np.arange(0, 0.2, 0.02)
        with self.assertRaisesRegex(ValueError, "must be of the same length"):
            NoiseLearnerV3Result.from_generators(generators, rates)

    def test_from_generators_different_num_qubits(self):
        """Test ``.from_generators`` raises if the generators have different numbers of qubits."""
        generators = [
            QubitSparsePauliList.from_label(pauli1 + pauli0)
            for pauli1 in "IXYZ"
            for pauli0 in "IXYZ"
        ][1:]
        generators[4] = QubitSparsePauliList.from_label("XII")
        rates = np.arange(0, 0.3, 0.02)
        with self.assertRaisesRegex(ValueError, "number of qubits"):
            NoiseLearnerV3Result.from_generators(generators, rates)

    def test_to_pauli_lindblad_map(self):
        """Test ``NoiseLearnerV3Result.to_pauli_lindblad_map``."""
        generators = [
            QubitSparsePauliList.from_list(list_)
            for list_ in [
                ["IX", "ZX"],
                ["IY", "ZY"],
                ["IZ"],
                ["XI", "XZ"],
                ["XX", "YY"],
                ["XY", "YX"],
                ["YI", "YZ"],
                ["ZI"],
                ["ZZ"],
            ]
        ]
        rates = np.arange(0, 0.18, 0.02)
        result = NoiseLearnerV3Result.from_generators(generators, rates)
        flatenned_generators = QubitSparsePauliList.from_list(
            [pauli1 + pauli0 for pauli1 in "IXYZ" for pauli0 in "IXYZ"][1:]
        )
        flatenned_rates = [
            0,
            0.02,
            0.04,
            0.06,
            0.08,
            0.1,
            0.06,
            0.12,
            0.1,
            0.08,
            0.12,
            0.14,
            0,
            0.02,
            0.16,
        ]
        self.assertEqual(
            result.to_pauli_lindblad_map().simplify(),
            PauliLindbladMap.from_components(flatenned_rates, flatenned_generators).simplify(),
        )


@ddt
class TestNoiseLearnerV3Results(IBMTestCase):
    """Tests the ``NoiseLearnerV3Results`` class."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.generators = [
            QubitSparsePauliList.from_label(pauli1 + pauli0)
            for pauli1 in "IXYZ"
            for pauli0 in "IXYZ"
        ][1:]
        self.rates = [np.linspace(0, i * 0.1, 15) for i in range(3)]
        self.results = [
            NoiseLearnerV3Result.from_generators(self.generators, rates) for rates in self.rates
        ]
        self.pauli_lindblad_maps = [result.to_pauli_lindblad_map() for result in self.results]
        self.inject_noise_annotations = [InjectNoise(ref, site="after") for ref in ["hi", "bye"]]
        self.tag_annotations = [Tag(ref) for ref in ["ciao", "arrivederci"]]

    def test_properties_of_iterable(self):
        """Test elementary methods of ``NoiseLearnerV3Results``.

        Elements: ``__init__``, ``__len__``, ``__get_item__``.
        """
        results = NoiseLearnerV3Results(self.results, metadata := {"this is": "metadata"})
        self.assertEqual(results.data, self.results, metadata)
        self.assertEqual(results[1], self.results[1])
        self.assertEqual(len(results), 3)

    @data("inject_noise", "tag")
    def test_to_dict_valid_input_require_refs_true(self, group_by):
        """Test ``NoiseLearnerV3Results.to_dict`` when ``require_refs`` is ``True``."""
        annotations = (
            self.inject_noise_annotations if group_by == "inject_noise" else self.tag_annotations
        )
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        returned_dict = NoiseLearnerV3Results(self.results[:2]).to_dict(
            circuit.data, True, group_by=group_by
        )
        self.assertDictEqual(
            {
                annotation.ref: pauli_lindblad_map
                for annotation, pauli_lindblad_map in zip(
                    annotations[:2], self.pauli_lindblad_maps[:2]
                )
            },
            returned_dict,
        )

    @data("inject_noise", "tag")
    def test_to_dict_valid_input_require_refs_false(self, group_by):
        """Test ``NoiseLearnerV3Results.to_dict`` when ``require_refs`` is ``True``."""
        annotations = (
            self.inject_noise_annotations if group_by == "inject_noise" else self.tag_annotations
        )
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        returned_dict = NoiseLearnerV3Results(self.results).to_dict(
            circuit.data, False, group_by=group_by
        )
        self.assertDictEqual(
            {
                annotation.ref: pauli_lindblad_map
                for annotation, pauli_lindblad_map in zip(
                    annotations,
                    [self.pauli_lindblad_maps[0], self.pauli_lindblad_maps[2]],
                )
            },
            returned_dict,
        )

    @data("inject_noise", "tag")
    def test_to_dict_wrong_num_of_instructions(self, group_by):
        """Test ``.to_dict`` raises if number of instructions does not match number of results."""
        annotations = (
            self.inject_noise_annotations if group_by == "inject_noise" else self.tag_annotations
        )
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "Expected 3 instructions but found 2"):
            NoiseLearnerV3Results(self.results).to_dict(circuit.data, True, group_by=group_by)

    @data("inject_noise", "tag")
    def test_to_dict_invalid_for_require_refs_true(self, group_by):
        """Test raising if an instruction does not contain annotations when requires_ref.

        Test that ``NoiseLearnerV3Results.to_dict`` raises if an instruction does not contain
        an annotation, when ``requires_ref`` is ``True``.
        """
        annotations = (
            self.inject_noise_annotations if group_by == "inject_noise" else self.tag_annotations
        )
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "without an inject noise"):
            NoiseLearnerV3Results(self.results).to_dict(circuit.data, True, group_by=group_by)

    @data("inject_noise", "tag")
    def test_to_dict_unboxed_instruction(self, group_by):
        """Test ``.to_dict`` raises if there is an instruction not in a box."""
        annotations = (
            self.inject_noise_annotations if group_by == "inject_noise" else self.tag_annotations
        )
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "contain a box"):
            NoiseLearnerV3Results(self.results).to_dict(circuit.data, group_by=group_by)

    @data("inject_noise", "tag")
    def test_to_dict_ref_used_twice(self, group_by):
        """Test ``.to_dict`` raises if an annotation reference is repeated."""
        annotations = (
            self.inject_noise_annotations if group_by == "inject_noise" else self.tag_annotations
        )
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "multiple instructions with the same ``ref``"):
            NoiseLearnerV3Results(self.results).to_dict(circuit.data, group_by=group_by)

    def test_to_pauli_lindblad_maps(self):
        """Test ``.to_pauli_lindblad_maps``."""
        results = NoiseLearnerV3Results(self.results)
        self.assertEqual(results.to_pauli_lindblad_maps(), self.pauli_lindblad_maps)
