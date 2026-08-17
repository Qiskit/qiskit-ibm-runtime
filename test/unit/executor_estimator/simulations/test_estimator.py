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
from ddt import data, ddt
from qiskit.quantum_info import PauliLindbladMap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from samplomatic import InjectNoise, Tag
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.simulator import ExperimentalSimulatorOptions

from ....ibm_test_case import IBMTestCase
from .utils import (
    create_estimator_test_data,
    create_estimator_test_data_extended,
    create_local_mode_estimator,
    create_noise_model_without_noise,
)

if TYPE_CHECKING:
    import numpy.typing as npt


@ddt
class TestEstimatorWithNoise(IBMTestCase):
    """Tests Executor based EstimatorV2 using simulator with noise through local mode."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = FakeManilaV2()
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, backend=self.backend
        )

    def test_result_quality_for_different_resilience_levels(self):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increase with increasing resilience level.
        """
        pub, ideal_evs = create_estimator_test_data(self.backend, self.preset_pass_manager)

        # maps resilience level to error (compared to statevector simulation) for each observable
        errors: dict[int, npt.NDArray[np.float64]] = {}

        # Run Estimator with different resilience levels:
        for resilience_level in (0, 1, 2):
            estimator = create_local_mode_estimator(self.backend)
            estimator.options.resilience_level = resilience_level

            result = estimator.run([pub]).result()
            # We get one expectation value per observable:
            evs = result[0].data.evs
            errors[resilience_level] = np.abs(evs - ideal_evs)

        # Increased resilience level should translate into increased expectation value quality:
        debug_message = f"Error per resilience level: {errors}"

        np.testing.assert_array_less(errors[2], errors[1], err_msg=debug_message)
        np.testing.assert_array_less(errors[1], errors[0], err_msg=debug_message)

    @data(
        # PEC
        {"resilience": {"pec_mitigation": True}},
        # ZNE (PEA)
        {"resilience": {"zne_mitigation": True, "zne": {"amplifier": "pea"}}},
    )
    def test_result_quality_with_noise_injection(self, option_overrides):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increase with PEC.
        """
        backend = AerSimulator(basis_gates=["cz", "rz", "sx", "x"])
        preset_pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)

        pub, ideal_evs = create_estimator_test_data(backend, preset_pass_manager)

        # -- Run using base level Estimator with minor mitigation only:

        base_level_option_overrides = {
            "twirling": {
                "enable_gates": True,
                "enable_measure": True,
                "num_randomizations": 1000,
                "shots_per_randomization": 200,
            },
            "resilience": {
                "measure_mitigation": True,
            },
        }
        base_level_estimator = create_local_mode_estimator(backend)
        base_level_estimator.options.update(**base_level_option_overrides)

        # Add noise to every unique layer, independent of its content (gates or measurements).
        simulated_noise_model = {
            annotation.ref: PauliLindbladMap.from_list([("X" * layer.operation.num_qubits, 0.005)])
            for layer in base_level_estimator.find_unique_layers([pub])
            if (annotation := get_annotation(layer.operation, Tag))
        }
        base_level_estimator.options.experimental["simulator_options"] = (
            ExperimentalSimulatorOptions(
                noise_model=simulated_noise_model,
            )
        )

        # Run a noisy simulation using baselevel estimator:
        result = base_level_estimator.run([pub]).result()
        base_level_errors = np.abs(result[0].data.evs - ideal_evs)

        # -- Run using the Estimator in the test configuration (defined by test parametrization):

        estimator = create_local_mode_estimator(backend)
        estimator.options.experimental["simulator_options"] = ExperimentalSimulatorOptions(
            noise_model=simulated_noise_model,
        )
        estimator.options.update(**base_level_option_overrides)
        estimator.options.update(**option_overrides)
        # Run a noisy simulation, injecting the same noise as in the simulation
        injected_noise_model = {
            inject_noise_annotation.ref: simulated_noise_model[
                get_annotation(layer.operation, Tag).ref
            ]
            for layer in estimator.find_unique_layers([pub])
            if (inject_noise_annotation := get_annotation(layer.operation, InjectNoise))
        }
        estimator.options.resilience.noise_model = injected_noise_model
        result = estimator.run([pub]).result()
        errors = np.abs(result[0].data.evs - ideal_evs)

        # -- Compare tested Estimator EVs to base level Estimator:

        # Increased resilience level should translate into increased expectation value quality:
        debug_message = f"Error per resilience level: {errors}"
        np.testing.assert_array_less(errors, base_level_errors, err_msg=debug_message)


@ddt
class TestEstimatorWithoutNoise(IBMTestCase):
    """Tests Executor based EstimatorV2 using noise-less simulator through local mode."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = AerSimulator(basis_gates=["cz", "rz", "sx", "x"])
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, backend=self.backend
        )

    @data(
        # Vanilla
        {"resilience_level": 0},
        # Measurement Twirling + TREX
        {"resilience_level": 1},
        # ZNE (Gate folding)
        {"resilience_level": 2, "resilience": {"zne": {"extrapolator": "linear"}}},
        # PEC
        {
            "twirling": {"enable_gates": True, "enable_measure": True},
            "resilience": {"pec_mitigation": True, "measure_mitigation": True},
        },
        # ZNE (PEA)
        {
            "twirling": {"enable_gates": True, "enable_measure": True},
            "resilience": {
                "zne_mitigation": True,
                "zne": {"amplifier": "pea", "extrapolator": "linear"},
                "measure_mitigation": True,
            },
        },
    )
    def test_correct_estimates_with_noise_injection(self, option_overrides):
        """Tests Estimator configurations to produce correct results in a noise-less environment."""
        pub, ideal_evs = create_estimator_test_data_extended(self.backend, self.preset_pass_manager)

        estimator = create_local_mode_estimator(self.backend)
        estimator.options.update(**option_overrides)

        # TODO: no DD possible on AER without gate durations.
        # Need to test this for a fake backend (e.g. in noisy test).
        # estimator.options.dynamical_decoupling.enable = True

        if "resilience_level" not in option_overrides:
            # resilience_level defaults do not need a noise-model.
            # Only adding this for PEC / PEA:
            estimator.options.resilience.noise_model = create_noise_model_without_noise(
                estimator, pub
            )

        result = estimator.run([pub]).result()
        # We get one expectation value per observable:
        evs = result[0].data.evs

        # With no noise, we should get expectation values which are more or less equal to
        # ground truth.
        np.testing.assert_allclose(actual=evs, desired=ideal_evs, atol=0.025)
