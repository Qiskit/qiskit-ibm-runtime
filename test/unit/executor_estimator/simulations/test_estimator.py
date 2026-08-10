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
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

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

    def test_result_quality_for_different_resilience_levels(self):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increases with increasing resilience level.

        Compares the results against a statevector simulation.
        """
        # Use standard mirror circuit, but without measurements, as StatevectorEstimator does
        # not support them.
        circuit = make_mirror_circuit_with_phases(self.backend, add_measurement=False)
        isa_circuit = self.preset_pass_manager.run(circuit)

        # We want to run multiple random variants of the circuit to get different expectation
        # values and to improve statistical significance:
        num_randomizations = 5
        np.random.seed(42)
        parameters = np.random.uniform(
            0,
            2 * np.pi,
            size=(num_randomizations, circuit.num_parameters),
        )

        # Prepare a PUB with an observable to estimate expectation values on.
        # Using "ZZ" observable, as the mirror circuit has parametric rx gates, which should yield
        # variations on Z projection.
        observable = SparsePauliOp("ZZ").apply_layout(isa_circuit.layout)
        pub = (isa_circuit, [observable], parameters)

        # Calculate ground truth to compare the results against via a statevector simulation:
        statevector_estimator = StatevectorEstimator()
        statevector_result = statevector_estimator.run([pub]).result()
        statevector_evs = statevector_result[0].data.evs

        # Run Estimator with different resilience levels:
        mean_errors: dict[int, float] = {}
        for resilience_level in (0, 1, 2):
            options = EstimatorOptions(
                # The resilience level we want to run with:
                resilience_level=resilience_level,
                # Local mode means that the underlying Executor is running Aer simulation
                # instead of connecting to a real backend.
                experimental={"local_mode": True},
            )

            estimator = EstimatorV2(mode=self.backend, options=options)

            result = estimator.run([pub]).result()
            evs = result[0].data.evs
            mean_error = np.mean(np.abs(evs - statevector_evs))
            max_error = np.max(np.abs(evs - statevector_evs))
            # Assert a base-level of quality across all resilience levels:
            self.assertLessEqual(max_error, 0.15)
            mean_errors[resilience_level] = float(mean_error)

        print(f"Mean errors per resilience level: {mean_errors}")

        # Increased resilience level should translate into increased expectation value quality:
        self.assertGreater(mean_errors[0], mean_errors[1])
        self.assertGreater(mean_errors[1], mean_errors[2])
