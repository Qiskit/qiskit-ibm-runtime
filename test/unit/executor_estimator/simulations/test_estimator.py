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

"""Tests Executor based EstimatorV2 implementation using simulator through local mode."""

from __future__ import annotations

import numpy as np
from ddt import ddt
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases


@ddt
class TestEstimator(IBMTestCase):
    """Tests Executor based EstimatorV2 implementation using simulator through local mode."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = FakeManilaV2()
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, target=self.backend.target
        )

    def test_simple_mirror_circuit_correct_evs(self):
        """Tests EstimatorV2 expectation values of a simple RZ Gate Circuit with default options.

        Compares the results against a statevector simulation.
        """
        circuit = make_mirror_circuit_with_phases(self.backend, add_measurement=False)
        isa_circuit = self.preset_pass_manager.run(circuit)

        parameters = [np.pi, np.pi]
        num_randomizations = 5
        np.random.seed(42)
        parameters = np.random.uniform(
            0,
            2 * np.pi,
            size=(num_randomizations, circuit.num_parameters),
        )

        estimator = EstimatorV2(self.backend)
        estimator.options.experimental = {"local_mode": True}

        observable = SparsePauliOp("ZZ").apply_layout(isa_circuit.layout)

        pub = (isa_circuit, [observable], parameters)
        result = estimator.run([pub]).result()

        statevector_estimator = StatevectorEstimator()
        statevector_result = statevector_estimator.run([pub]).result()

        print(
            f"EstimatorV2 <ZZ> = {result[0].data.evs}, "
            + f"StatevectorEstimator <ZZ> = {statevector_result[0].data.evs}"
        )
        np.testing.assert_allclose(result[0].data.evs, statevector_result[0].data.evs, atol=0.15)
