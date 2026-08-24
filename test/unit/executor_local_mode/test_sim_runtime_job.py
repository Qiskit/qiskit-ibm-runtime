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

"""Test SimRuntimeJob."""

from unittest import skipUnless

from qiskit.utils import optionals

from qiskit_ibm_runtime.executor_local_mode import SimRuntimeJob
from qiskit_ibm_runtime.options_models.simulator import ExperimentalSimulatorOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.results import QuantumProgramResult

from ...ibm_test_case import IBMTestCase

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator


@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestSimRuntimeJob(IBMTestCase):
    """Tests for SimRuntimeJob."""

    def test_result(self):
        """Test that result returns a ``QuantumProgramResult``."""
        job = SimRuntimeJob(
            AerSimulator(method="stabilizer"), QuantumProgram(1), ExperimentalSimulatorOptions()
        )
        self.assertIsInstance(job.result(), QuantumProgramResult)
