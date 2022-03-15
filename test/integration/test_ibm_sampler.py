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

from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes

from qiskit_ibm_runtime import IBMSampler
from qiskit_ibm_runtime import BaseSampler, SamplerResult

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationIBMSampler(IBMIntegrationTestCase):
    """Integration tests for Sampler primitive."""

    @run_integration_test
    def test_sampler_primitive_non_parameterized_circuits(self, service):
        """Verify if sampler primitive returns expected results for non-parameterized circuits."""

        sampler_factory = IBMSampler(service=service, backend="ibmq_qasm_simulator")

        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()

        # executes a Bell circuit
        with sampler_factory(circuits=[bell]) as sampler:
            self.assertIsInstance(sampler, BaseSampler)

            circuit_indices = [0]
            result = sampler(circuit_indices=circuit_indices, parameter_values=[[]])
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), len(circuit_indices))
            self.assertEqual(len(result.metadata), len(circuit_indices))

        # executes three Bell circuits
        with sampler_factory([bell] * 3) as sampler:
            self.assertIsInstance(sampler, BaseSampler)

            circuit_indices1 = [0, 1, 2]
            result1 = sampler(
                circuit_indices=circuit_indices1, parameter_values=[[]] * 3
            )
            self.assertIsInstance(result1, SamplerResult)
            self.assertEqual(len(result1.quasi_dists), len(circuit_indices1))
            self.assertEqual(len(result1.metadata), len(circuit_indices1))

            circuit_indices2 = [0, 2]
            result2 = sampler(
                circuit_indices=circuit_indices2, parameter_values=[[]] * 2
            )
            self.assertIsInstance(result2, SamplerResult)
            self.assertEqual(len(result2.quasi_dists), len(circuit_indices2))
            self.assertEqual(len(result2.metadata), len(circuit_indices2))

            circuit_indices3 = [1, 2]
            result3 = sampler(
                circuit_indices=circuit_indices3, parameter_values=[[]] * 2
            )
            self.assertIsInstance(result3, SamplerResult)
            self.assertEqual(len(result3.quasi_dists), len(circuit_indices3))
            self.assertEqual(len(result3.metadata), len(circuit_indices3))

    @run_integration_test
    def test_sampler_primitive_parameterized_circuits(self, service):
        """Verify if sampler primitive returns expected results for parameterized circuits."""

        sampler_factory = IBMSampler(service=service, backend="ibmq_qasm_simulator")

        # parameterized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with sampler_factory(circuits=[pqc, pqc2]) as sampler:
            self.assertIsInstance(sampler, BaseSampler)

            circuit_indices = [0, 0, 1]
            result = sampler(
                circuit_indices=circuit_indices,
                parameter_values=[theta1, theta2, theta3],
            )
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), len(circuit_indices))
            self.assertEqual(len(result.metadata), len(circuit_indices))
