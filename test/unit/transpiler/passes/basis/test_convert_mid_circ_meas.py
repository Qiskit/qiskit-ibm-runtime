# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test the conversion of terminal Measure to MidCircuitMeasure."""

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import Measure
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import PassManager

from qiskit_ibm_runtime.circuit import MidCircuitMeasure
from qiskit_ibm_runtime.transpiler.passes.basis.convert_mid_circ_meas import (
    ConvertToMidCircuitMeasure,
)

from .....ibm_test_case import IBMTestCase


class TestConvertToMidCircuitMeasure(IBMTestCase):
    """Tests the ConvertToMidCircuitMeasure pass"""

    def setUp(self):
        super().setUp()

        num_qubits = 5
        mcm = MidCircuitMeasure()
        self.target_without = GenericBackendV2(num_qubits=num_qubits, seed=0).target
        self.target_with = GenericBackendV2(num_qubits=num_qubits, seed=0).target
        self.target_with.add_instruction(mcm, {(i,): None for i in range(num_qubits)})

        self.qc = QuantumCircuit(2, 2)
        self.qc.x(0)
        self.qc.append(mcm, [0], [0])
        self.qc.measure([0], [0])
        self.qc.measure_all()

    def test_convert_default(self):
        """Test basic conversion to measure_2."""
        custom_pass = ConvertToMidCircuitMeasure(self.target_with)
        pm = PassManager([custom_pass])
        transpiled = pm.run(self.qc)

        # The transpiled circuit will contain measure_2 in the two mid-circ-measurements
        # and regular Measure instances in terminal measurements
        self.assertIsInstance(transpiled.data[1].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[2].operation, MidCircuitMeasure)
        # [3] is the barrier
        self.assertNotIsInstance(transpiled.data[4].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[4].operation, Measure)
        self.assertNotIsInstance(transpiled.data[5].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[5].operation, Measure)

    def test_convert_raises(self):
        """Test that value error is raised if measure_2 not supported in target."""
        with self.assertRaisesRegex(
            ValueError,
            r"measure_2 is not supported by the given target\. "
            r"Supported operations are: dict_keys\(\['cx', 'id', 'rz', "
            r"'sx', 'x', 'reset', 'delay', 'measure'\]\)",
        ):
            ConvertToMidCircuitMeasure(self.target_without)

    def test_convert_measure_3(self):
        """Test conversion with non-default alternative measure. The pass is
        only expected to convert terminal measures into measure_3, the existing
        measure_2 instruction is left untouched."""
        num_qubits = 5
        mcm = MidCircuitMeasure("measure_3")
        target = GenericBackendV2(num_qubits=num_qubits, seed=0).target
        target.add_instruction(mcm, {(i,): None for i in range(num_qubits)})

        custom_pass = ConvertToMidCircuitMeasure(target, "measure_3")
        pm = PassManager([custom_pass])
        transpiled = pm.run(self.qc)

        # The transpiled circuit will contain both measure_2 and measure_3
        self.assertIsInstance(transpiled.data[1].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[2].operation, MidCircuitMeasure)
        self.assertEqual(transpiled.data[1].operation.name, "measure_2")
        self.assertEqual(transpiled.data[2].operation.name, "measure_3")
        # [3] is the barrier
        self.assertNotIsInstance(transpiled.data[4].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[4].operation, Measure)
        self.assertNotIsInstance(transpiled.data[5].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[5].operation, Measure)

    def test_different_qarg(self):
        """Test that terminal measure is only replaced if measure_2 is defined
        in corresponding qarg (else, it's left untouched)."""
        num_qubits = 5
        mcm = MidCircuitMeasure()
        target = GenericBackendV2(num_qubits=num_qubits, seed=0).target
        # only define measure_2 in physical qubit 0
        target.add_instruction(mcm, {(0,): None})

        qc = QuantumCircuit(2, 2)
        qc.x(0)
        # place measure in qubit 1
        qc.measure([1], [1])
        qc.measure_all()

        custom_pass = ConvertToMidCircuitMeasure(target)
        pm = PassManager([custom_pass])
        transpiled = pm.run(qc)

        # The transpiled circuit will not contain any MidCircuitMeasure instance
        self.assertNotIsInstance(transpiled.data[1].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[1].operation, Measure)
        # [2] is the barrier
        self.assertNotIsInstance(transpiled.data[3].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[3].operation, Measure)
        self.assertNotIsInstance(transpiled.data[4].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[4].operation, Measure)
