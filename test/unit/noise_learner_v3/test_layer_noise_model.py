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

"""Tests the ``LayerNoiseModel`` class."""

import numpy as np
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.quantum_info import QubitSparsePauliList
from samplomatic import InjectNoise, Tag, Twirl

from qiskit_ibm_runtime.noise_learner_v3.layer_noise_model import LayerNoiseModel
from qiskit_ibm_runtime.results.noise_learner_v3 import NoiseLearnerV3Result

from ...ibm_test_case import IBMTestCase


@ddt
class TestLayerNoiseModel(IBMTestCase):
    """Tests the ``LayerNoiseModel`` class."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        generators = [
            QubitSparsePauliList.from_label(pauli1 + pauli0)
            for pauli1 in "IXYZ"
            for pauli0 in "IXYZ"
        ][1:]
        rates = [np.linspace(0, i * 0.1, 15) for i in range(3)]
        self.pauli_lindblad_maps = [
            NoiseLearnerV3Result.from_generators(generators, r).to_pauli_lindblad_map()
            for r in rates
        ]
        self.inject_noise_annotations = [InjectNoise(ref, site="after") for ref in ["hi", "bye"]]
        self.tag_annotations = [Tag(ref) for ref in ["ciao", "arrivederci"]]

    @data("injection", "simulation")
    def test_to_dict_valid_input_require_refs_true(self, mode):
        """Test ``LayerNoiseModel.to_dict`` when ``require_refs`` is ``True``."""
        annotations = self.inject_noise_annotations if mode == "injection" else self.tag_annotations
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        returned_dict = LayerNoiseModel(circuit.data, self.pauli_lindblad_maps[:2]).to_dict(
            require_refs=True, mode=mode
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

    @data("injection", "simulation")
    def test_to_dict_valid_input_require_refs_false(self, mode):
        """Test ``LayerNoiseModel.to_dict`` when ``require_refs`` is ``False``."""
        annotations = self.inject_noise_annotations if mode == "injection" else self.tag_annotations
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        returned_dict = LayerNoiseModel(circuit.data, self.pauli_lindblad_maps).to_dict(
            require_refs=False, mode=mode
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

    @data("injection", "simulation")
    def test_init_raises(self, mode):
        """Test ``LayerNoiseModel.__init__`` raises if number of layers does not match maps."""
        circuit = QuantumCircuit(2)
        annotations = self.inject_noise_annotations if mode == "injection" else self.tag_annotations
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "does not match"):
            LayerNoiseModel(circuit.data, self.pauli_lindblad_maps)

    @data("injection", "simulation")
    def test_to_dict_invalid_for_require_refs_true(self, mode):
        """Test raising if an instruction does not contain annotations when require_refs is True.

        Test that ``LayerNoiseModel.to_dict`` raises if an instruction does not contain
        an annotation, when ``require_refs`` is ``True``.
        """
        annotations = self.inject_noise_annotations if mode == "injection" else self.tag_annotations
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "without an inject noise"):
            LayerNoiseModel(circuit.data, self.pauli_lindblad_maps).to_dict(
                require_refs=True, mode=mode
            )

    @data("injection", "simulation")
    def test_to_dict_unboxed_instruction(self, mode):
        """Test ``.to_dict`` raises if there is an instruction not in a box."""
        annotations = self.inject_noise_annotations if mode == "injection" else self.tag_annotations
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "contain a box"):
            LayerNoiseModel(circuit.data, self.pauli_lindblad_maps).to_dict(mode=mode)

    @data("injection", "simulation")
    def test_to_dict_ref_used_twice(self, mode):
        """Test ``.to_dict`` raises if an annotation reference is repeated."""
        annotations = self.inject_noise_annotations if mode == "injection" else self.tag_annotations
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl(), annotations[0]]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[annotations[1]]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(ValueError, "multiple instructions with the same ``ref``"):
            LayerNoiseModel(circuit.data, self.pauli_lindblad_maps).to_dict(mode=mode)
