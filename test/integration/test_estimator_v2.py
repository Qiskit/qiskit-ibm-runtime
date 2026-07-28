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

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from ddt import ddt
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.base import BaseEstimatorV2  # noqa: TC002
from qiskit.quantum_info import SparsePauliOp

if TYPE_CHECKING:
    from qiskit.transpiler import StagedPassManager
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import EstimatorV2 as EstimatorV2Native
from qiskit_ibm_runtime import EstimatorV2 as EstimatorV2ThroughExecutor

from ..ibm_test_case import IBMIntegrationTestCase


def create_bell_isa_circuit_with_single_rz_on_q0(
    preset_pass_manager: StagedPassManager,
) -> QuantumCircuit:
    """Create a Bell circuit with a single RZ parameter on q0, transpiled to ISA."""
    circuit = QuantumCircuit(2, name="Bell with single parameter")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rz(Parameter("q0_phase"), 0)

    return preset_pass_manager.run(circuit)


@ddt
class _TestEstimatorBase(IBMIntegrationTestCase):
    """An integration test, testing different EstimatorV2 implementations."""

    estimator_variant: type[BaseEstimatorV2] | None = None

    def setUp(self):
        """Test level setup."""
        if self.estimator_variant is None:
            self.skipTest("This base class cannot be run as a standalone testcase.")
        super().setUp()
        self.backend = self.service.backend(self.dependencies.qpu)

        self.pm = generate_preset_pass_manager(optimization_level=1, target=self.backend.target)

    def test_estimator_works_for_basic_circuit_with_no_options(self):
        """Runs a simple parametric circuit with multiple observables to make sure the basics work.

        Tests
        - Job completes without exceptions
        - Correct expectation value shapes
        """
        isa_circuit = create_bell_isa_circuit_with_single_rz_on_q0(self.pm)

        zz_with_offset = SparsePauliOp.from_list([("ZZ", 1.0), ("II", 9.0)]).apply_layout(
            isa_circuit.layout
        )
        # q0_phase = 0 -> 10.0 q0_phase = pi -> 10

        xx_with_offset = SparsePauliOp.from_list([("XX", 1.0), ("II", 3.0)]).apply_layout(
            isa_circuit.layout
        )
        # q0_phase = 0 -> 4.0 q0_phase = pi -> 2.0

        estimator = self.estimator_variant(self.backend)

        job = estimator.run(
            pubs=[
                # Map all parameter sets to all observables
                (isa_circuit, [[zz_with_offset], [xx_with_offset]], [[0], [np.pi]]),
                # Map each parameter set to one observable:
                (isa_circuit, [zz_with_offset, xx_with_offset], [[0], [np.pi]]),
            ]
        )

        results = job.result()

        # Expect one result per pub:
        self.assertEqual(len(results), 2)

        # 4 Expectation values should have been calculated for full broadcasting:
        self.assertEqual(results[0].data.evs.shape, (2, 2))

        # 2 Expectation values should have been calculated for 1 to 1 parameter mapping:
        self.assertEqual(results[1].data.evs.shape, (2,))


class TestEstimatorNative(_TestEstimatorBase):
    """Variant of the Estimator integration test, running through native Estimator."""

    estimator_variant = EstimatorV2Native


class TestEstimatorThroughExecutor(_TestEstimatorBase):
    """Variant of the Estimator integration test, running through Executor based Estimator."""

    estimator_variant = EstimatorV2ThroughExecutor
