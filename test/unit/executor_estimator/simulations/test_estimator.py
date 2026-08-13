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
from .utils import create_estimator_test_data, create_local_mode_estimator

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
            optimization_level=1, target=self.backend.target
        )

    def test_result_quality_for_different_resilience_levels(self):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increase with increasing resilience level.
        """
        # FIXME: add_projector_observables=False is only needed,
        # due to a bug in TREX post-processing:
        # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
        pub, ideal_evs = create_estimator_test_data(
            self.backend, self.preset_pass_manager, add_projector_observables=False
        )

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

    def test_result_quality_for_pec(self):
        """Tests the effect of resilience on EstimatorV2 results.

        Estimator result quality is expected to increase with PEC.
        """
        backend = AerSimulator(basis_gates=["cz", "rz", "sx", "x"])
        preset_pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)

        estimator = create_local_mode_estimator(backend)
        estimator.options.resilience.measure_mitigation = True
        estimator.options.twirling.enable_gates = True
        estimator.options.twirling.enable_measure = True
        estimator.options.twirling.num_randomizations = 1000
        estimator.options.twirling.shots_per_randomization = 200

        # maps bool (whether we applied PEC or not) to errors for each observable
        errors: dict[bool, npt.NDArray[np.float64]] = {}

        # FIXME: add_projector_observables=False is only needed,
        # due to a bug in TREX post-processing:
        # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
        pub, ideal_evs = create_estimator_test_data(
            backend, preset_pass_manager, add_projector_observables=False
        )

        # Add noise to every unique layer, independent of its content (gates or measurements).
        simulated_noise_model = {
            annotation.ref: PauliLindbladMap.from_list([("X" * layer.operation.num_qubits, 0.005)])
            for layer in estimator.find_unique_layers([pub])
            if (annotation := get_annotation(layer.operation, Tag))
        }
        estimator.options.experimental["simulator_options"] = ExperimentalSimulatorOptions(
            noise_model=simulated_noise_model,
        )

        # Run a noisy simulation without PEC
        estimator.options.resilience.pec_mitigation = False
        result = estimator.run([pub]).result()
        errors[False] = np.abs(result[0].data.evs - ideal_evs)

        # Run a noisy simulation with PEC, injecting the same noise as in the simulation
        estimator.options.resilience.pec_mitigation = True
        injected_noise_model = {
            inject_noise_annotation.ref: simulated_noise_model[
                get_annotation(layer.operation, Tag).ref
            ]
            for layer in estimator.find_unique_layers([pub])
            if (inject_noise_annotation := get_annotation(layer.operation, InjectNoise))
        }
        estimator.options.resilience.noise_model = injected_noise_model
        result = estimator.run([pub]).result()
        errors[True] = np.abs(result[0].data.evs - ideal_evs)

        # Increased resilience level should translate into increased expectation value quality:
        debug_message = f"Error per resilience level: {errors}"
        np.testing.assert_array_less(errors[True], errors[False], err_msg=debug_message)


@ddt
class TestEstimatorWithoutNoise(IBMTestCase):
    """Tests Executor based EstimatorV2 using noise-less simulator through local mode."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = AerSimulator()
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, basis_gates=["cz", "rz", "sx", "x"]
        )

    @data(0, 1, 2)
    def test_correct_estimates_for_different_resilience_levels(self, resilience_level):
        """Tests that EstimatorV2 produces correct results in a noise-less environment.

        Parametrized to run with all three estimator resilience levels.
        """
        # FIXME: add_projector_observables=False is only needed,
        # due to a bug in TREX post-processing affecting resilience levels > 0:
        # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
        add_projector_observables = True if resilience_level == 0 else False

        pub, ideal_evs = create_estimator_test_data(
            self.backend,
            self.preset_pass_manager,
            add_projector_observables=add_projector_observables,
        )

        estimator = create_local_mode_estimator(self.backend)
        estimator.options.resilience_level = resilience_level

        result = estimator.run([pub]).result()
        # We get one expectation value per observable:
        evs = result[0].data.evs

        # With no noise, we should get expectation values which are more or less equal to
        # ground truth.
        np.testing.assert_allclose(actual=evs, desired=ideal_evs, atol=0.02)

    def test_correct_estimates_with_pec(self):
        """Tests that EstimatorV2 with PEC produces correct results in a noise-less environment."""
        pub, ideal_evs = create_estimator_test_data(self.backend, self.preset_pass_manager)

        estimator = create_local_mode_estimator(self.backend)
        estimator.options.resilience.pec_mitigation = True
        estimator.options.twirling.enable_gates = True
        estimator.options.twirling.enable_measure = True

        # FIXME: TREX currently not possible for the projector observables we use here:
        # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
        # estimator.options.resilience.measure_mitigation = True

        # TODO: no DD possible on AER without gate durations.
        # Need to test this for a fake backend (e.g. in noisy test).
        # estimator.options.dynamical_decoupling.enable = True

        layers = [
            layer
            for layer in estimator.find_unique_layers([pub])
            if get_annotation(layer.operation, InjectNoise)
        ]

        # In a noise-less simulation we do not expect noise. So we can construct the noise_model
        # with empty noise for all layers:
        noise_model = {
            get_annotation(layer.operation, InjectNoise).ref: PauliLindbladMap.identity(
                layer.operation.num_qubits
            )
            for layer in layers
        }

        estimator.options.resilience.noise_model = noise_model

        result = estimator.run([pub]).result()
        # We get one expectation value per observable:
        evs = result[0].data.evs

        # With no noise, we should get expectation values which are more or less equal to
        # ground truth.
        np.testing.assert_allclose(actual=evs, desired=ideal_evs, atol=0.02)
