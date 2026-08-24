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
from ddt import data, ddt, unpack
from qiskit.quantum_info import PauliLindbladMap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.simulator import ExperimentalSimulatorOptions

from ....ibm_test_case import IBMTestCase
from .utils import (
    compute_sem_theoretical,
    create_estimator_test_data,
    create_estimator_test_data_extended,
    create_estimator_test_data_with_groupings,
    create_local_mode_estimator,
    create_noise_model_without_noise,
)

if TYPE_CHECKING:
    import numpy.typing as npt


RESILIENCE_LEVEL_0 = {"resilience_level": 0}

RESILIENCE_LEVEL_1 = {"resilience_level": 1}

RESILIENCE_LEVEL_2_LINEAR = {
    "resilience_level": 2,
    "resilience": {"zne": {"extrapolator": "linear"}},
}

TWIRLING_TREX_PEC = {
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {"pec_mitigation": True, "measure_mitigation": True},
}

TWIRLING_TREX_PEA = {
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {
        "zne_mitigation": True,
        "zne": {"amplifier": "pea"},
        "measure_mitigation": True,
    },
}

TWIRLING_TREX_PEA_LINEAR = {
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {
        "zne_mitigation": True,
        "zne": {"amplifier": "pea", "extrapolator": "linear"},
        "measure_mitigation": True,
    },
}

TWIRLING_TREX = {
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {"measure_mitigation": True},
}


@ddt
class TestEstimatorWithNoise(IBMTestCase):
    """Tests Executor based EstimatorV2 using simulator with noise through local mode."""

    def setUp(self):
        """Test level setup."""
        super().setUp()

    def test_result_quality_for_different_resilience_levels(self):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increase with increasing resilience level.
        """
        backend = FakeManilaV2()
        preset_pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)

        pub, ideal_evs = create_estimator_test_data(backend, preset_pass_manager)

        # maps resilience level to error (compared to statevector simulation) for each observable
        errors: dict[int, npt.NDArray[np.float64]] = {}

        # Run Estimator with different resilience levels:
        for resilience_level in (0, 1, 2):
            estimator = create_local_mode_estimator(
                backend,
                num_randomizations=100,
                shots_per_randomization=200,
                options_overrides={"resilience_level": resilience_level},
            )

            result = estimator.run([pub]).result()
            # We get one expectation value per observable:
            evs = result[0].data.evs
            errors[resilience_level] = np.abs(evs - ideal_evs)

        # Increased resilience level should translate into increased expectation value quality:
        debug_message = f"Error per resilience level: {errors}"

        np.testing.assert_array_less(errors[2], errors[1], err_msg=debug_message)
        np.testing.assert_array_less(errors[1], errors[0], err_msg=debug_message)

    @data(
        TWIRLING_TREX_PEC,
        TWIRLING_TREX_PEA,
    )
    def test_result_quality_with_noise_injection(self, option_overrides):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increase with PEC.
        """
        backend = AerSimulator(basis_gates=["cz", "rz", "sx", "x"])
        preset_pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)

        pub, ideal_evs = create_estimator_test_data(backend, preset_pass_manager)

        # -- Run using base level Estimator with minor mitigation only:

        base_level_estimator = create_local_mode_estimator(
            backend,
            num_randomizations=1000,
            shots_per_randomization=200,
            options_overrides=TWIRLING_TREX,
        )

        # Add noise to every unique layer, independent of its content (gates or measurements).
        layers = base_level_estimator.find_unique_layers([pub], types="all")
        simulated_noise_model = [
            (layer, PauliLindbladMap.from_list([("X" * layer.operation.num_qubits, 0.005)]))
            for layer in layers
        ]

        base_level_estimator.options.experimental["simulator_options"] = (
            ExperimentalSimulatorOptions(
                layer_noise_model=simulated_noise_model,
            )
        )

        # Run a noisy simulation using baselevel estimator:
        result = base_level_estimator.run([pub]).result()
        base_level_errors = np.abs(result[0].data.evs - ideal_evs)

        # -- Run using the Estimator in the test configuration (defined by test parametrization):

        estimator = create_local_mode_estimator(
            backend,
            num_randomizations=1000,
            shots_per_randomization=200,
            options_overrides=option_overrides,
        )
        estimator.options.experimental["simulator_options"] = ExperimentalSimulatorOptions(
            layer_noise_model=simulated_noise_model,
        )
        # Run a noisy simulation, injecting the same noise as in the simulation
        injected_noise_model = {
            inject_noise_annotation.ref: PauliLindbladMap.from_list(
                [("X" * layer.operation.num_qubits, 0.005)]
            )
            for layer in estimator.find_unique_layers([pub], types="gates")
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
        RESILIENCE_LEVEL_0,
        RESILIENCE_LEVEL_1,
        RESILIENCE_LEVEL_2_LINEAR,
        TWIRLING_TREX_PEC,
        TWIRLING_TREX_PEA,
    )
    def test_correct_estimates_with_noise_injection(self, option_overrides):
        """Tests Estimator configurations to produce correct results in a noise-less environment."""
        pub, ideal_evs = create_estimator_test_data_extended(self.backend, self.preset_pass_manager)

        estimator = create_local_mode_estimator(
            self.backend,
            num_randomizations=100,
            shots_per_randomization=200,
            options_overrides=option_overrides,
        )

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


@ddt
class TestEstimatorNoiselessStatistical(IBMTestCase):
    """Statistical validation of noiseless EstimatorV2 results.

    In a noiseless run, the reported expectation values should be very close to the
    true (ideal) values, and how close depends only on the number of shots taken.
    These tests check that both:

    1. The expectation values are close to the ideal values, within a tolerance
       derived from shot noise.
    2. The uncertainty the Estimator reports (``ensemble_standard_error``) matches
       what we'd theoretically expect for that number of shots.

    Increasing NUM_RANDOMIZATIONS and SHOTS_PER_RANDOMIZATION improves test accuracy
    (tightens the bounds), while reducing K_SIGMA improves test accuracy at the cost of higher
    false negative rate.
    """

    NUM_RANDOMIZATIONS = 100
    SHOTS_PER_RANDOMIZATION = 200
    K_SIGMA = 4.5  # False negative rate 1 in 147000

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = AerSimulator(basis_gates=["cz", "rz", "sx", "x"])
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, backend=self.backend
        )

    @data(
        ("vanilla", RESILIENCE_LEVEL_0),
        ("pec", TWIRLING_TREX_PEC),
    )
    @unpack
    def test_statistical_accuracy(self, name, option_overrides):
        """Checks expectation values and reported uncertainty against theoretical predictions.

        For each observable, this verifies that:
        1. The expectation value is sufficiently close to the ideal value.
        2. The reported ``ensemble_standard_error`` is sufficiently close to the
           theoretically expected uncertainty.
        """
        estimator = create_local_mode_estimator(
            self.backend,
            num_randomizations=self.NUM_RANDOMIZATIONS,
            shots_per_randomization=self.SHOTS_PER_RANDOMIZATION,
            options_overrides=option_overrides,
        )

        pubs, ideal_evs_list, groupings = create_estimator_test_data_with_groupings(
            self.backend, self.preset_pass_manager, estimator.options.resilience.measure_mitigation
        )

        if name == "pec":
            # Build a combined noise model covering all unique layers across both pubs.
            noise_model = create_noise_model_without_noise(estimator, pubs[0])
            for pub in pubs[1:]:
                noise_model.update(create_noise_model_without_noise(estimator, pub))
            estimator.options.resilience.noise_model = noise_model

        result = estimator.run(pubs).result()
        n_total = self.NUM_RANDOMIZATIONS * self.SHOTS_PER_RANDOMIZATION
        # ese tolerance: 5σ on the chi-squared estimator sqrt(ensemble_variance/N)
        ese_tolerance = self.K_SIGMA / np.sqrt(2 * (n_total - 1))

        for pub_idx, (pub, ideal_evs, term_group_indices_per_pub) in enumerate(
            zip(pubs, ideal_evs_list, groupings)
        ):
            evs = result[pub_idx].data.evs
            ese = result[pub_idx].data.ensemble_standard_error
            ideal_evs_arr = np.asarray(ideal_evs)

            sem_theoretical = compute_sem_theoretical(
                pub.observables.tolist(),
                pub.circuit,
                pub.parameter_values.as_array(),
                self.NUM_RANDOMIZATIONS,
                self.SHOTS_PER_RANDOMIZATION,
                term_group_indices_per_pub,
            )

            # --- Assertion 1: point estimate within 5σ of ideal ---
            ev_deviations = np.abs(evs.flatten() - ideal_evs_arr)
            np.testing.assert_array_less(
                ev_deviations,
                self.K_SIGMA * sem_theoretical,
                err_msg=(
                    f"[{name}, pub{pub_idx}] EV deviations exceed {self.K_SIGMA}σ: "
                    f"deviations={ev_deviations}, sem_theoretical={sem_theoretical}"
                ),
            )

            # --- Assertion 2: ese within 5σ of theoretical SEM (vanilla only) ---
            # Note: TREX error propagation is not accounted for (issue #2858)
            # in neither the test nor the code.
            ese_rel_deviations = np.abs(ese.flatten() - sem_theoretical) / sem_theoretical
            np.testing.assert_array_less(
                ese_rel_deviations,
                ese_tolerance,
                err_msg=(
                    f"[{name}, pub{pub_idx}] ensemble_standard_error deviations exceed "
                    f"{self.K_SIGMA}σ: relative deviations={ese_rel_deviations}, "
                    f"tolerance={ese_tolerance:.4f}, ese={ese}, "
                    f"sem_theoretical={sem_theoretical}"
                ),
            )
