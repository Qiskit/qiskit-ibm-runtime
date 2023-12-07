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
from qiskit.quantum_info import SparsePauliOp
from qiskit.test.reference_circuits import ReferenceCircuits

# pylint: disable=unused-import
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Estimator

from ..ibm_test_case import IBMTestCase
from .mock.fake_runtime_service import FakeRuntimeService


class TestRunSimulation(IBMTestCase):
    """Tests for local execution on simulators"""

    def test_basic_flow(self):
        """Test basic flow on simulator."""
        # service = QiskitRuntimeService(channel="ibm_quantum")

        # service = FakeRuntimeService(channel="ibm_quantum")  # pylint: disable=unused-variable
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        shots = 100
        circuit = ReferenceCircuits.bell()
        for backend in ["fake_manila", AerSimulator()]:
            sampler = Sampler(backend=backend)
            job = sampler.run(circuit, shots=shots)
            result = job.result()
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.2)
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.2)
            self.assertEqual(result.metadata[0]["shots"], shots)

            estimator = Estimator(backend=backend)
            obs = SparsePauliOp("ZZ")
            job = estimator.run([circuit], observables=obs, shots=shots)
            result = job.result()
            self.assertAlmostEqual(result.values[0], 1.0, delta=0.01)
            self.assertEqual(result.metadata[0]["shots"], shots)

    def test_aer_sim_options(self):
        """Test that options to Aer simulator are passed properly"""
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        shots = 100
        circuit = ReferenceCircuits.bell()
        sim_methods = [
            "statevector",
            "density_matrix",
            "stabilizer",
            "extended_stabilizer",
            "matrix_product_state",
        ]
        for method in sim_methods:
            backend = AerSimulator(method=method)
            sampler = Sampler(backend=backend)
            job = sampler.run(circuit, shots=shots)
            result = job.result()
            print("***")
            self.assertEqual(result.metadata[0]["simulator_metadata"]["method"], method)
