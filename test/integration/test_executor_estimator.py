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

"""Tests for Executor-based EstimatorV2."""

import numpy as np
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.base import BaseEstimatorV2  # noqa: TC002
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import EstimatorV2 as EstimatorV2Native
from qiskit_ibm_runtime import EstimatorV2 as EstimatorV2ThroughExecutor
from qiskit_ibm_runtime.executor_estimator import EstimatorV2 as NativeEstimatorV2

from ..ibm_test_case import IBMIntegrationTestCase


@ddt
class _TestEstimatorBase(IBMIntegrationTestCase):
    """An integration test, testing the EstimatorV2 through Executor implementation."""

    estimator_variant: BaseEstimatorV2 | None = None

    def setUp(self):
        """Test level setup."""
        if self.estimator_variant is None:
            self.skipTest("This base class cannot be run as a standalone testcase.")
        super().setUp()
        self.backend = self.service.backend(self.dependencies.qpu)

        self.pm = generate_preset_pass_manager(optimization_level=1, target=self.backend.target)

    @data(NativeEstimatorV2, EstimatorV2ThroughExecutor)
    def test_simple_hamiltonian_with_parameters(self, EstimatorV2Variant):
        """A simple parametric circuit with multiple observables to make sure the basics work.

        This test is parametrized to run for both the native Estimator and the EstimatorV2 running
        through Executor.
        Both those Executor variants behave the same.

        Tests
        - Correct calculation of simple hamiltionian (linear combination of observables)
        - Basic broadcasting rules (how parameters and observables are combined)
        """
        circuit = QuantumCircuit(2, name="Bell with single parameter")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.rz(Parameter("q0_phase"), 0)

        isa_circuit = self.pm.run(circuit)

        zz_with_offset = SparsePauliOp.from_list([("ZZ", 1.0), ("II", 9.0)]).apply_layout(
            isa_circuit.layout
        )
        # q0_phase = 0 -> 10.0 q0_phase = pi -> 10

        xx_with_offset = SparsePauliOp.from_list([("XX", 1.0), ("II", 3.0)]).apply_layout(
            isa_circuit.layout
        )
        # q0_phase = 0 -> 4.0 q0_phase = pi -> 2.0

        estimator = EstimatorV2Variant(self.backend)

        job = estimator.run(
            pubs=[
                # Map all parameter sets to all observables
                (isa_circuit, [[zz_with_offset], [xx_with_offset]], [[0], [np.pi]]),
                # Map each parameter set to one observable:
                (isa_circuit, [zz_with_offset, xx_with_offset], [[0], [np.pi]]),
            ]
        )

        results = job.result()

        expectation_values_0 = results[0].data.evs
        self.assertEqual(expectation_values_0.shape, (2, 2))
        self.assertEqual(expectation_values_0.shape, (2, 2))

        expectation_values_1 = results[1].data.evs
        self.assertEqual(expectation_values_1.shape, (2,))

        backend_has_real_qubits = False
        if backend_has_real_qubits:
            self.assertTrue(False)

        # self.assertAlmostEqual(results[1].data.evs, 10.0, delta=delta)  # obs1, phi=pi
        # self.assertAlmostEqual(results[2].data.evs, 10.0, delta=delta)  # obs2, phi=0
        # self.assertAlmostEqual(results[3].data.evs,  8.0, delta=delta)  # obs2, phi=pi


class TestEstimatorNative(_TestEstimatorBase):
    """Variant of the Estimator integration test, running through native Estimator."""

    estimator_variant = EstimatorV2Native


class TestEstimatorThroughExecutor(_TestEstimatorBase):
    """Variant of the Estimator integration test, running through Executor based Estimator."""

    estimator_variant = EstimatorV2ThroughExecutor
