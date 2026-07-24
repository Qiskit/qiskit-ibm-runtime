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

"""Test AerExecutor and AerRuntimeJob."""

from unittest import skipUnless

from qiskit.utils import optionals

from qiskit_ibm_runtime.aer_executor import AerExecutor, AerRuntimeJob
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.results import QuantumProgramResult

from ...ibm_test_case import IBMTestCase

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator


@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestAerExecutor(IBMTestCase):
    """Tests for AerExecutor."""

    def test_run(self):
        """Test that run returns an `AerRuntimeJob`."""
        executor = AerExecutor(AerSimulator(method="stabilizer"))
        self.assertIsInstance(executor, AerExecutor)
        self.assertIsInstance(executor.run(QuantumProgram(1)), AerRuntimeJob)


@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestAerRuntimeJob(IBMTestCase):
    """Tests for AerRuntimeJob."""

    def test_result(self):
        """Test that result returns a `QuantumProgramResult`."""
        job = AerRuntimeJob(AerSimulator(method="stabilizer"), QuantumProgram(1))
        self.assertIsInstance(job.result(), QuantumProgramResult)
