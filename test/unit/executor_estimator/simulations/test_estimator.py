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

from typing import TYPE_CHECKING

import numpy as np
from ddt import ddt
from qiskit import QuantumCircuit
from qiskit.primitives import ObservablesArray, StatevectorEstimator
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.simulator import ExperimentalSimulatorOptions

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases

if TYPE_CHECKING:
    import numpy.typing as npt


@ddt
class TestEstimatorErrorMitigationEfficacy(IBMTestCase):
    """Tests the efficacy of error mitigation in the Executor based EstimatorV2 implementation.

    The tests use noisy simulations to verify that expectation values get closer to the ideal
    result as the mitigation is applied.
    """

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = FakeManilaV2()
        # self.backend = AerSimulator()
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, target=self.backend.target
        )

    def test_result_quality_for_different_resilience_levels(self):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increase with increasing resilience level.

        Compares the results against a statevector simulation.
        """
        # Use standard mirror circuit, but without measurements, as StatevectorEstimator does
        # not support them.
        circuit = make_mirror_circuit_with_phases(self.backend, add_measurement=False)
        isa_circuit = self.preset_pass_manager.run(circuit)

        # Select values for the rx gates:
        parameters = np.array([3.5 * np.pi / 4] * circuit.num_parameters)

        # Prepare a PUB with multiple observables to estimate expectation values on.
        # Using "Z" observables, as the mirror circuit has parametric rx gates, which should yield
        # variations on Z projection.
        observables = [
            SparsePauliOp(pauli_string).apply_layout(isa_circuit.layout)
            for pauli_string in ["ZZ", "IZ", "ZI"]
        ]
        pub = (isa_circuit, observables, parameters)

        # Calculate ground truth to compare the results against via a statevector simulation:
        statevector_estimator = StatevectorEstimator()
        statevector_result = statevector_estimator.run([pub]).result()
        statevector_evs = statevector_result[0].data.evs

        # maps resilience level to error (compared to statevector simulation) for each observable
        errors: dict[int, npt.NDArray[np.float64]] = {}

        # Run Estimator with different resilience levels:
        for resilience_level in (0, 1, 2):
            options = EstimatorOptions(
                # The resilience level we want to run with:
                resilience_level=resilience_level,
                # Local mode means that the underlying Executor is running Aer simulation
                # instead of connecting to a real backend.
                experimental={
                    "local_mode": True,
                    "simulator_options": ExperimentalSimulatorOptions(seed_simulator=42),
                },
            )
            options.twirling.num_randomizations = 100
            options.twirling.shots_per_randomization = 200
            options.default_shots = 100 * 200

            estimator = EstimatorV2(mode=self.backend, options=options)

            result = estimator.run([pub]).result()
            # We get one expectation value per observable:
            evs = result[0].data.evs
            errors[resilience_level] = np.abs(evs - statevector_evs)

        # Increased resilience level should translate into increased expectation value quality:
        debug_message = f"Error per resilience level: {errors}"
        np.testing.assert_array_less(errors[2], errors[1], err_msg=debug_message)
        np.testing.assert_array_less(errors[1], errors[0], err_msg=debug_message)

        # Resilience level 2 should give very accurate expectation value:
        np.testing.assert_array_less(errors[2], 0.025, err_msg=debug_message)


@ddt
class TestEstimatorCorrectness(IBMTestCase):
    """Tests the correctness of Executor based EstimatorV2 implementation.

    The tests use noiseless simulations to verify the expectation values against
    theoretical results.
    """

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = GenericBackendV2(5, noise_info=False, seed=972)
        # self.backend = AerSimulator()
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, target=self.backend.target
        )
        self.tolerance = 2  # In terms of stansdard deviations

    def test_vanilla_correctness(self):
        """Tests the correctness of vanilla estimator (no error mitigation)."""
        target_precision = 0.01

        circuit = QuantumCircuit(3)
        theta = np.pi / 8
        circuit.rx(theta, 0)
        circuit.rx(-np.pi / 2, 1)
        circuit.ry(np.pi / 2, 2)

        isa_circuit = self.preset_pass_manager.run(circuit)

        observable_pairs: list[tuple[str, float]] = [
            ("IIZ", np.cos(theta)),
            ("IYZ", np.cos(theta)),
            ("XIZ", np.cos(theta)),
            ("1IZ", 0.5 * np.cos(theta)),
            ("IYr", np.sin(np.pi / 4 - theta / 2) ** 2),
            ("X+I", 0.5),
            ("0IZ", 0.5 * np.cos(theta)),
            ("IYl", np.cos(np.pi / 4 - theta / 2) ** 2),
            ("X-I", 0.5),
            ("ZXY", 0),
        ]
        observables = ObservablesArray.coerce([obs_string for obs_string, _ in observable_pairs])
        isa_observables = observables.apply_layout(isa_circuit.layout)
        pub = (isa_circuit, isa_observables)

        options = EstimatorOptions(
            resilience_level=0,
            experimental={
                "local_mode": True,
                # "simulator_options": ExperimentalSimulatorOptions(seed_simulator=42),
            },
        )
        options.twirling.enable_gates = True
        options.default_precision = target_precision

        estimator = EstimatorV2(mode=self.backend, options=options)
        result = estimator.run([pub]).result()
        errors = [
            abs(expected[1] - res) for expected, res in zip(observable_pairs, result[0].data.evs)
        ]

        # Test the maximal deviation \ reported std
        # Base distribution N[0, target_precision]
        self.assertLess(max(errors), self.tolerance * target_precision)
        self.assertLess(
            max(result[0].data.ensemble_standard_error), self.tolerance * target_precision
        )

        # Test the mean of the deviations \ reported stds
        # Distribution of the mean N[0.8 * target_precision, 0.6 * target_precision / np.sqrt(N)]
        expected_mean = 0.8 * target_precision
        expected_mean_std = 0.6 * target_precision / np.sqrt(len(observable_pairs))
        self.assertLess(np.mean(errors), expected_mean + self.tolerance * expected_mean_std)
        self.assertGreater(np.mean(errors), expected_mean - self.tolerance * expected_mean_std)
        self.assertLess(
            np.mean(result[0].data.ensemble_standard_error),
            expected_mean + self.tolerance * expected_mean_std,
        )
        self.assertGreater(
            np.mean(result[0].data.ensemble_standard_error),
            expected_mean - self.tolerance * expected_mean_std,
        )
