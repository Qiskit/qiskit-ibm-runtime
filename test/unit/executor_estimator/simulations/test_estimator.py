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
from samplomatic import InjectNoise, Tag
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.simulator import ExperimentalSimulatorOptions

from ....ibm_test_case import IBMTestCase
from .utils import (
    compute_sem_theoretical,
    create_estimator_test_data,
    create_estimator_test_data_extended,
    create_estimator_test_data_statistical,
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

        estimator = create_local_mode_estimator(
            backend,
            num_randomizations=1000,
            shots_per_randomization=200,
            options_overrides=option_overrides,
        )
        estimator.options.experimental["simulator_options"] = ExperimentalSimulatorOptions(
            noise_model=simulated_noise_model,
        )
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

    For a noiseless simulation with R randomizations of S shots (N = R×S total), the
    estimator output x̄ is the mean of R independent per-randomization expectation values.
    Each per-randomization value is itself the mean of S bounded, independent shot outcomes
    (eigenvalues ±1 for Paulis). By the CLT with R ≥ 100, x̄ is extremely well-approximated
    as normally distributed:

        x̄ ~ N(μ, SEM²)   where SEM = sqrt(Var_pp[O] / N)

    The theoretical SEM is derived from an exact statevector simulation, mirroring the
    post-processor's grouping of Pauli terms by measurement basis. Within each group,
    all terms share the same shots and their combined variance is computed as
    Var[Σ c_k P_k] (including cross-covariances). Groups use independent shot batches
    so their variances add. No shot data is involved. Tests then verify:

    1. The point estimate lies within 5 standard errors of the ideal value:
       |evs − ideal| ≤ 5 × SEM_theoretical
       (false-positive probability ≈ 5.7 × 10⁻⁷ per observable)

    2. The reported ``ensemble_standard_error`` matches the theoretical SEM to
       within 5 standard deviations of its own estimation error:
       |ese − SEM_theoretical| / SEM_theoretical ≤ 5 / sqrt(2 × (N − 1))
       ≈ 2.5% for N = 20 000 — a tight regression test on the variance calculation.

       ``ensemble_standard_error`` uses all N shots as an iid ensemble (relative
       precision ~1/sqrt(2N) ≈ 0.5% for N = 20 000), making it far more tightly
       constrained than ``stds`` (which uses only R per-twirl averages, ~7%).

       Testing ``ensemble_standard_error ≈ SEM_theoretical`` also implicitly verifies
       the simulation is truly noiseless: in a noisy run, twirling adds inter-randomization
       variance so that ``stds > ensemble_standard_error``, which would break this assertion.

    Two PUBs are tested per configuration:
    - PUB 0: three single-Pauli-string observables (each a single measurement config).
    - PUB 1: one multi-term observable ``1·IYI + 2·IYY + 3·IZI`` where IYI and IYY
      commute (same measurement config, non-trivial cross-covariances) while IZI
      anticommutes with both (independent config). This exercises the cross-covariance
      correction in the post-processor.

    Configurations tested: vanilla (resilience_level=0) and PEC with identity noise model.
    PEC with an identity noise model is statistically identical to vanilla because the PEC
    gamma factor equals 1 (all Lindblad rates are zero) and no errors are ever injected.
    """

    NUM_RANDOMIZATIONS = 100
    SHOTS_PER_RANDOMIZATION = 200
    K_SIGMA = 5.0

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
        """Tests point-estimate accuracy and reported uncertainty against theoretical predictions.

        Runs both PUBs from ``create_estimator_test_data_statistical`` and for each
        observable checks:
        1. The EV is within 5 × SEM_theoretical of the ideal value.
        2. (vanilla only) The reported ``ensemble_standard_error`` is within 2.5% of
           SEM_theoretical (5σ on the chi-squared variance estimator).

        Assertion 2 is skipped for PEC because the TREX scale factor is a deterministic
        constant in the post-processor (its estimation uncertainty from the calibration
        circuit is not propagated into ``ensemble_standard_error``). This means the
        reported ``ese`` under PEC can differ from ``SEM_theoretical`` by more than the
        shot-noise-only tolerance without indicating a bug. Assertion 1 already exercises
        the PEC code path for correctness of the point estimate.
        """
        pubs, ideal_evs_list = create_estimator_test_data_statistical(
            self.backend, self.preset_pass_manager
        )

        estimator = create_local_mode_estimator(
            self.backend,
            num_randomizations=self.NUM_RANDOMIZATIONS,
            shots_per_randomization=self.SHOTS_PER_RANDOMIZATION,
            options_overrides=option_overrides,
        )

        if name == "pec":
            # Build a combined noise model covering all unique layers across both pubs.
            noise_model = create_noise_model_without_noise(estimator, pubs[0])
            noise_model.update(create_noise_model_without_noise(estimator, pubs[1]))
            estimator.options.resilience.noise_model = noise_model

        result = estimator.run(pubs).result()
        n_total = self.NUM_RANDOMIZATIONS * self.SHOTS_PER_RANDOMIZATION
        # ese tolerance: 5σ on the chi-squared estimator sqrt(ensemble_variance/N)
        ese_tolerance = self.K_SIGMA / np.sqrt(2 * (n_total - 1))

        for pub_idx, (pub, ideal_evs) in enumerate(zip(pubs, ideal_evs_list)):
            isa_circuit, observables, parameters = pub
            evs = result[pub_idx].data.evs
            ese = result[pub_idx].data.ensemble_standard_error
            ideal_evs_arr = np.asarray(ideal_evs)

            sem_theoretical = compute_sem_theoretical(
                observables if isinstance(observables, list) else [observables],
                isa_circuit,
                parameters,
                self.NUM_RANDOMIZATIONS,
                self.SHOTS_PER_RANDOMIZATION,
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
            if name == "vanilla":
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
