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
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases

if TYPE_CHECKING:
    import numpy.typing as npt


@ddt
class TestEstimator(IBMTestCase):
    """Tests Executor based EstimatorV2 implementation using simulator through local mode."""

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

        # Select values for the rz gates:
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
                experimental={"local_mode": True},
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
