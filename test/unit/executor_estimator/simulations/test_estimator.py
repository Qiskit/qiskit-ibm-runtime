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
from qiskit.circuit import Parameter
from qiskit.primitives import ObservablesArray
from qiskit.quantum_info import PauliLindbladMap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases

if TYPE_CHECKING:
    import numpy.typing as npt


def create_estimator_test_data(backend, preset_pass_manager, add_projector_observables=True):
    """Create a pub and ground truth expectation values for it."""
    # Use standard mirror circuit.
    # - No measurements, as StatevectorEstimator does not support them.
    # - No trailing Rx gates, as we want to add our own rotations
    circuit = make_mirror_circuit_with_phases(
        backend, num_qubits=3, add_measurement=False, add_rx=False
    )

    # Add rotations to become sensitive to X, Y, Z observables:
    circuit.rx(Parameter("rx_0"), 0)
    circuit.rx(Parameter("rx_1"), 1)
    circuit.ry(Parameter("ry_2"), 2)
    isa_circuit = preset_pass_manager.run(circuit)
    theta = np.pi / 8
    parameters = [theta, -np.pi / 2, np.pi / 2]

    observable_ground_truth_pairs: list[tuple[str, float]] = [
        ("IIZ", np.cos(theta)),
        ("IYZ", np.cos(theta)),
        ("XIZ", np.cos(theta)),
    ]
    if add_projector_observables:
        observable_ground_truth_pairs.extend(
            [
                ("1IZ", 0.5 * np.cos(theta)),
                ("IYr", np.sin(np.pi / 4 - theta / 2) ** 2),
                ("X+I", 0.5),
                ("0IZ", 0.5 * np.cos(theta)),
                ("IYl", np.cos(np.pi / 4 - theta / 2) ** 2),
                ("X-I", 0.5),
            ]
        )

    # Prepare a PUB with multiple observables to estimate expectation values on.
    observables = ObservablesArray.coerce(
        [obs_string for obs_string, _ in observable_ground_truth_pairs]
    ).apply_layout(isa_circuit.layout)
    pub = (isa_circuit, observables, parameters)

    return pub, [ev for _, ev in observable_ground_truth_pairs]


def create_local_mode_estimator(backend):
    """Creates an estimator instance running local mode simulation.

    The returned instance has all mitigation disabled (resilience_level 0)
    """
    options = EstimatorOptions(
        # Select resilience level 0 by default, disabling all mitigation:
        resilience_level=0,
        # Local mode means that the underlying Executor is running Aer simulation
        # instead of connecting to a real backend.
        experimental={
            "local_mode": True,
            ## Set a fixed seed for the simulator to reduce flakiness and to allow
            ## tighter error asserts.
            # "simulator_options": ExperimentalSimulatorOptions(seed_simulator=42),
        },
    )

    # Increase number of shots to have better statistics:
    options.default_precision = 0.01
    # options.twirling.num_randomizations = 100
    # options.twirling.shots_per_randomization = 200
    # options.default_shots = 100 * 200

    return EstimatorV2(mode=backend, options=options)


@ddt
class TestEstimatorWithNoise(IBMTestCase):
    """Tests Executor based EstimatorV2 using simulator with noise through local mode."""

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
        # FIXME: add_projector_observables=False is only needed,
        # due to a bug in TREX post-processing:
        # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
        pub, statevector_evs = create_estimator_test_data(
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
            errors[resilience_level] = np.abs(evs - statevector_evs)

        # Increased resilience level should translate into increased expectation value quality:
        debug_message = f"Error per resilience level: {errors}"

        np.testing.assert_array_less(errors[2], errors[1], err_msg=debug_message)
        np.testing.assert_array_less(errors[1], errors[0], err_msg=debug_message)

        # Resilience level 2 should give very accurate expectation value:
        # With fixed simulator seed, we can have 0.025 here.
        # Without we should set to something like 0.04 to reduce flakiness.
        np.testing.assert_array_less(errors[2], 0.04, err_msg=debug_message)


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

    def test_correct_estimates_without_mitigation(self):
        """Tests that vanilla EstimatorV2 produces correct results in a noise-less environment.

        Compares the results against a statevector simulation.
        """
        pub, statevector_evs = create_estimator_test_data(self.backend, self.preset_pass_manager)

        estimator = create_local_mode_estimator(self.backend)

        result = estimator.run([pub]).result()
        # We get one expectation value per observable:
        evs = result[0].data.evs

        # With no noise, we should get expectation values which are more or less equal to
        # ground truth.
        np.testing.assert_almost_equal(actual=evs, desired=statevector_evs, decimal=2)

    def test_correct_estimates_with_pec(self):
        """Tests that EstimatorV2 with PEC produces correct results in a noise-less environment.

        Compares the results against a statevector simulation.
        """
        pub, statevector_evs = create_estimator_test_data(self.backend, self.preset_pass_manager)

        estimator = create_local_mode_estimator(self.backend)
        estimator.options.resilience.pec_mitigation = True

        layers = [
            layer
            for layer in estimator.find_unique_layers([pub])
            if get_annotation(layer.operation, InjectNoise)
        ]

        # In a noise-less simulation we do not expect noise. So we can construct the noise_model
        # with empty noise for all layers:
        noise_model = {
            get_annotation(layer.operation, InjectNoise).ref: PauliLindbladMap.from_sparse_list(
                [], num_qubits=layer.operation.num_qubits
            )
            for layer in layers
        }

        estimator.options.resilience.noise_model = noise_model

        result = estimator.run([pub]).result()
        # We get one expectation value per observable:
        evs = result[0].data.evs
        print(evs)

        # With no noise, we should get expectation values which are more or less equal to
        # ground truth.
        np.testing.assert_almost_equal(actual=evs, desired=statevector_evs, decimal=2)
