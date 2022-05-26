# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for Sampler primitive."""

from qiskit.circuit.library import RealAmplitudes
from qiskit.test.reference_circuits import ReferenceCircuits

from qiskit_ibm_runtime import Sampler, BaseSampler, SamplerResult

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationIBMSampler(IBMIntegrationTestCase):
    """Integration tests for Sampler primitive."""

    @run_integration_test
    def test_sampler_primitive_non_parameterized_circuits(self, service):
        """Verify if sampler primitive returns expected results for non-parameterized circuits."""

        options = {"backend": "ibmq_qasm_simulator"}

        bell = ReferenceCircuits.bell()

        # executes a Bell circuit
        with Sampler(circuits=bell, service=service, options=options) as sampler:
            self.assertIsInstance(sampler, BaseSampler)

            circuits0 = [0]
            result = sampler(circuits=circuits0, parameter_values=[[]])
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), len(circuits0))
            self.assertEqual(len(result.metadata), len(circuits0))
            self.assertAlmostEqual(result.quasi_dists[0]["11"], 0.5, delta=0.05)
            self.assertAlmostEqual(result.quasi_dists[0]["00"], 0.5, delta=0.05)

        # executes three Bell circuits
        with Sampler(circuits=[bell] * 3, service=service, options=options) as sampler:
            self.assertIsInstance(sampler, BaseSampler)

            circuits1 = [0, 1, 2]
            result1 = sampler(circuits=circuits1, parameter_values=[[]] * 3)
            self.assertIsInstance(result1, SamplerResult)
            self.assertEqual(len(result1.quasi_dists), len(circuits1))
            self.assertEqual(len(result1.metadata), len(circuits1))
            for i in range(len(circuits1)):
                self.assertAlmostEqual(result1.quasi_dists[i]["11"], 0.5, delta=0.05)
                self.assertAlmostEqual(result1.quasi_dists[i]["00"], 0.5, delta=0.05)

            circuits2 = [0, 2]
            result2 = sampler(circuits=circuits2, parameter_values=[[]] * 2)
            self.assertIsInstance(result2, SamplerResult)
            self.assertEqual(len(result2.quasi_dists), len(circuits2))
            self.assertEqual(len(result2.metadata), len(circuits2))
            for i in range(len(circuits2)):
                self.assertAlmostEqual(result2.quasi_dists[i]["11"], 0.5, delta=0.05)
                self.assertAlmostEqual(result2.quasi_dists[i]["00"], 0.5, delta=0.05)

            circuits3 = [1, 2]
            result3 = sampler(circuits=circuits3, parameter_values=[[]] * 2)
            self.assertIsInstance(result3, SamplerResult)
            self.assertEqual(len(result3.quasi_dists), len(circuits3))
            self.assertEqual(len(result3.metadata), len(circuits3))
            for i in range(len(circuits3)):
                self.assertAlmostEqual(result3.quasi_dists[i]["11"], 0.5, delta=0.05)
                self.assertAlmostEqual(result3.quasi_dists[i]["00"], 0.5, delta=0.05)

    @run_integration_test
    def test_sampler_primitive_parameterized_circuits(self, service):
        """Verify if sampler primitive returns expected results for parameterized circuits."""

        options = {"backend": "ibmq_qasm_simulator"}

        # parameterized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with Sampler(circuits=[pqc, pqc2], service=service, options=options) as sampler:
            self.assertIsInstance(sampler, BaseSampler)

            circuits0 = [pqc, pqc, pqc2]
            result = sampler(
                circuits=circuits0,
                parameter_values=[theta1, theta2, theta3],
            )
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), len(circuits0))
            self.assertEqual(len(result.metadata), len(circuits0))
