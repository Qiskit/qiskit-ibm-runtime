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

"""Tests the class ``QuantumProgramResult``."""

import numpy as np

from qiskit_ibm_runtime.quantum_program.quantum_program_result import QuantumProgramResult

from ...ibm_test_case import IBMTestCase


class TestQuantumProgramResult(IBMTestCase):
    """Tests the ``QuantumProgramResult`` class."""

    def test_quantum_program_result(self):
        """Tests the ``QuantumProgramResult`` class."""
        meas1 = np.array([[False], [True], [True]])
        meas2 = np.array([[True, True], [True, False], [False, False]])
        meas_flips = np.array([[False, False]])

        result1 = {"meas": meas1}
        result2 = {"meas": meas2, "measurement_flips.meas": meas_flips}
        result = QuantumProgramResult([result1, result2])

        # test __len__
        self.assertEqual(len(result), 2)

        # test __iter__
        for res, expected_res in zip(result, [result1, result2]):
            self.assertDictEqual(res, expected_res)

        # test __getitem__
        self.assertEqual([result[0], result[1]], [result1, result2])
