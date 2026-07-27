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

"""Test SimExecutor and SimRuntimeJob."""

from unittest import skipUnless

from qiskit.quantum_info import PauliLindbladMap
from qiskit.utils import optionals

from qiskit_ibm_runtime.options_models.executor import ExecutorOptions
from qiskit_ibm_runtime.options_models.simulator import SimulatorOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.results import QuantumProgramResult
from qiskit_ibm_runtime.sim_executor import SimExecutor, SimRuntimeJob

from ...ibm_test_case import IBMTestCase

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator


@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestSimExecutor(IBMTestCase):
    """Tests for SimExecutor."""

    def test_options_setter(self):
        """Test that ``__setattr__``handles options correctly."""
        backend = AerSimulator(method="stabilizer")
        executor = SimExecutor(backend)
        self.assertIsInstance(executor.options, ExecutorOptions)
        self.assertIsNone(executor.options.simulator.noise_model)

        noise_model = {
            "tag1": PauliLindbladMap.from_list([("IIIXI", 0.1), ("XXIII", 0.3), ("IIYIY", 0.4)])
        }

        executor.options = {"simulator": {"noise_model": noise_model}}
        self.assertIsInstance(executor.options, ExecutorOptions)
        self.assertIsNotNone(executor.options.simulator.noise_model)

    def test_run(self):
        """Test that run returns an ``SimRuntimeJob``."""
        executor = SimExecutor(AerSimulator(method="stabilizer"))
        self.assertIsInstance(executor, SimExecutor)
        self.assertIsInstance(executor.run(QuantumProgram(1)), SimRuntimeJob)


@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestSimRuntimeJob(IBMTestCase):
    """Tests for SimRuntimeJob."""

    def test_result(self):
        """Test that result returns a ``QuantumProgramResult``."""
        job = SimRuntimeJob(
            AerSimulator(method="stabilizer"), QuantumProgram(1), SimulatorOptions()
        )
        self.assertIsInstance(job.result(), QuantumProgramResult)
