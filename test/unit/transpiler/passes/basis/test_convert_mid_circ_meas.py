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

    def test_transpile_with(self):
        custom_pass = ConvertToMidCircuitMeasure(self.target_with)
        pm = PassManager([custom_pass])
        transpiled = pm.run(self.qc)
        self.assertIsInstance(transpiled.data[1].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[2].operation, MidCircuitMeasure)
        # [3] is the barrier
        self.assertNotIsInstance(transpiled.data[4].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[4].operation, Measure)
        self.assertNotIsInstance(transpiled.data[5].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[5].operation, Measure)

    def test_transpile_without(self):
        custom_pass = ConvertToMidCircuitMeasure(self.target_without)
        pm = PassManager([custom_pass])
        transpiled = pm.run(self.qc)
        self.assertIsInstance(transpiled.data[1].operation, MidCircuitMeasure)
        self.assertNotIsInstance(transpiled.data[2].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[2].operation, Measure)
        # [3] is the barrier
        self.assertNotIsInstance(transpiled.data[4].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[4].operation, Measure)
        self.assertNotIsInstance(transpiled.data[5].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[5].operation, Measure)
