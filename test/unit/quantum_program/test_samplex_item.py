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

"""Tests the ``SamplexItem`` class."""

import numpy as np

from samplomatic import build, Twirl, InjectNoise

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem


from ...ibm_test_case import IBMTestCase


class TestSamplexItem(IBMTestCase):
    """Tests the ``SamplexItem`` class."""

    def test_samplex_item(self):
        """Test ``SamplexItem`` for a valid input."""
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl()]):
            circuit.rx(Parameter("p"), 0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()

        template_circuit, samplex = build(circuit)

        parameter_values = np.array([[[1], [2]], [[3], [4]], [[5], [6]]])
        shape = (30, 1, 2)

        samplex_item = SamplexItem(
            template_circuit,
            samplex,
            samplex_arguments={"parameter_values": parameter_values},
            shape=shape,
            chunk_size=7,
        )
        self.assertEqual(samplex_item.samplex, samplex)
        self.assertEqual(samplex_item.circuit, template_circuit)
        self.assertEqual(samplex_item.chunk_size, 7)
        self.assertEqual(samplex_item.shape, (30, 3, 2))
        self.assertTrue(
            np.array_equal(samplex_item.samplex_arguments["parameter_values"], parameter_values)
        )

    def test_samplex_item_shape_not_broadcastable(self):
        """Test that ``SamplexItem`` raises an error when the samplex shape does not match
        the parameter values."""
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl()]):
            circuit.rx(Parameter("p"), 0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()

        template_circuit, samplex = build(circuit)

        parameter_values = np.array([[[1], [2]], [[3], [4]], [[5], [6]]])
        shape = (30, 2, 2)

        with self.assertRaisesRegex(ValueError, "must be broadcastable"):
            SamplexItem(
                template_circuit,
                samplex,
                samplex_arguments={"parameter_values": parameter_values},
                shape=shape,
            )

    def test_samplex_item_no_params(self):
        """Test ``SamplexItem`` when there are no parameters."""
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()

        template_circuit, samplex = build(circuit)

        samplex_item = SamplexItem(template_circuit, samplex)
        self.assertEqual(samplex_item.samplex, samplex)
        self.assertEqual(samplex_item.circuit, template_circuit)
        self.assertEqual(samplex_item.chunk_size, None)
        self.assertEqual(samplex_item.shape, ())

    def test_samplex_item_num_params_doesnt_match_circuit_arguments(self):
        """Test that ``SamplexItem`` raises an error if the number of circuit parameters
        doesn't match the shape of the samplex arguments."""
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl()]):
            circuit.rx(Parameter("p"), 0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()

        template_circuit, samplex = build(circuit)

        parameter_values = np.array([[3, 10], [4, 11], [5, 12]])
        with self.assertRaisesRegex(ValueError, "expects an array ending with shape"):
            SamplexItem(
                template_circuit, samplex, samplex_arguments={"parameter_values": parameter_values}
            )

    def test_samplex_item_no_samplex_arguments_for_parametric_circuit(self):
        """Test that ``SamplexItem`` raises an error if the circuit has parameters
        but the ``samplex_arguments`` parameter is unset."""
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl()]):
            circuit.rx(Parameter("p"), 0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()

        template_circuit, samplex = build(circuit)

        with self.assertRaisesRegex(ValueError, "parameter values to use during sampling"):
            SamplexItem(template_circuit, samplex)

    def test_samplex_item_with_noise(self):
        """Test ``SamplexItem`` with noise annotations."""
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), InjectNoise(ref="r0")]):
            circuit.rx(Parameter("p"), 0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl(), InjectNoise(ref="r1")]):
            circuit.measure_all()

        template_circuit, samplex = build(circuit)

        parameter_values = np.array([[[1], [2]], [[3], [4]], [[5], [6]]])
        pauli_lindblad_maps = {
            "r0": PauliLindbladMap.from_list([("IX", 0.04), ("XX", 0.05)]),
            "r1": PauliLindbladMap.from_list([("XI", 0.02), ("IZ", 0.035)]),
        }

        samplex_item = SamplexItem(
            template_circuit,
            samplex,
            samplex_arguments={
                "parameter_values": parameter_values,
                "pauli_lindblad_maps": pauli_lindblad_maps,
            },
        )
        self.assertEqual(samplex_item.samplex, samplex)
        self.assertEqual(samplex_item.circuit, template_circuit)
        self.assertEqual(samplex_item.chunk_size, None)
        self.assertEqual(samplex_item.shape, (3, 2))
        self.assertTrue(
            np.array_equal(samplex_item.samplex_arguments["parameter_values"], parameter_values)
        )
        self.assertEqual(
            samplex_item.samplex_arguments["pauli_lindblad_maps.r0"], pauli_lindblad_maps["r0"]
        )
        self.assertEqual(
            samplex_item.samplex_arguments["pauli_lindblad_maps.r1"], pauli_lindblad_maps["r1"]
        )

    def test_samplex_item_missing_pauli_lindblad_map_in_samplex_arguments(self):
        """Test that ``SamplexItem`` raises an error when the samplex arguments don't contain
        a Pauli-Lindblad map for a noise annotation."""
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl(), InjectNoise(ref="r0")]):
            circuit.rx(Parameter("p"), 0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl(), InjectNoise(ref="r1")]):
            circuit.measure_all()

        template_circuit, samplex = build(circuit)

        parameter_values = np.array([[[1], [2]], [[3], [4]], [[5], [6]]])
        pauli_lindblad_maps = {"r0": PauliLindbladMap.from_list([("IX", 0.04), ("XX", 0.05)])}

        with self.assertRaisesRegex(ValueError, "pauli_lindblad_maps.r1"):
            SamplexItem(
                template_circuit,
                samplex,
                samplex_arguments={
                    "parameter_values": parameter_values,
                    "pauli_lindblad_maps": pauli_lindblad_maps,
                },
            )
