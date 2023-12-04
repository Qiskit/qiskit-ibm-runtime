# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for running locally on a simulator."""

from qiskit_aer import AerSimulator

from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler

from ..ibm_test_case import IBMTestCase
from .mock.fake_runtime_service import FakeRuntimeService


class TestRunSimulation(IBMTestCase):
    """Class for testing the Sampler class."""

    def test_basic_flow(self):
        """Test basic flow on simulator."""
        #service = QiskitRuntimeService(channel="ibm_quantum")
        service = FakeRuntimeService()
        shots = 1000
        for backend in ["manila", AerSimulator()]:
            circuit = ReferenceCircuits.bell()
            sampler = Sampler(backend=backend)
            job = sampler.run(circuit, skip_transpilation=True, shots=shots)
            result = job.result()
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.2)
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.2)

            self.assertEqual(result.metadata[0]["shots"], shots)
