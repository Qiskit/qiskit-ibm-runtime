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

"""Utilities for running tests against local-mode executor-based Estimator."""

from __future__ import annotations

import numpy as np
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator, SparsePauliOp

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

from ....utils import make_mirror_circuit_with_phases


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
    observables = [
        SparsePauliOp.from_operator(Operator.from_label(obs_string)).apply_layout(
            isa_circuit.layout
        )
        for obs_string, _ in observable_ground_truth_pairs
    ]

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
    options.twirling.num_randomizations = 100
    options.twirling.shots_per_randomization = 200
    options.default_shots = 100 * 200

    return EstimatorV2(mode=backend, options=options)
