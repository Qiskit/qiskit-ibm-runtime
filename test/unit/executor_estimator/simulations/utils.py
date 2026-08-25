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

from typing import TYPE_CHECKING

import numpy as np
from qiskit.circuit import Parameter
from qiskit.primitives import ObservablesArray
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

from ....utils import make_mirror_circuit_with_phases

if TYPE_CHECKING:
    from typing import Any

    from qiskit.providers import BackendV2


def create_estimator_test_data(backend, preset_pass_manager, include_projectors):
    """Create a pub and ideal expectation values for it.

    The circuit will use 3 qubits and only a subset of observable combinations.
    """
    circuit = make_mirror_circuit_with_phases(
        backend, num_qubits=3, add_measurement=False, add_rx=False
    )

    circuit.rx(Parameter("rx_0"), 0)
    circuit.rx(Parameter("rx_1"), 1)
    circuit.ry(Parameter("ry_2"), 2)
    isa_circuit = preset_pass_manager.run(circuit)

    theta = np.pi / 5
    phi = np.pi / 3
    parameters = [theta, -phi, 3 * np.pi / 4]

    y_q1 = np.sin(phi)
    z_q0 = np.cos(theta)
    r_q1 = (1 + np.sin(phi)) / 2
    l_q0 = (1 + np.sin(theta)) / 2
    x_q2 = np.sqrt(2) / 2

    observable_ideal_ev_pairs: list[tuple[str, float]] = [
        ("IYZ", y_q1 * z_q0),  # ≈ 0.701
        ("XII", x_q2),  # ≈ 0.707
    ]

    if include_projectors:
        observable_ideal_ev_pairs.append(("Irl", r_q1 * l_q0))  # ≈ 0.741

    observables = ObservablesArray([obs for obs, _ in observable_ideal_ev_pairs])
    observables = observables.apply_layout(isa_circuit.layout)

    pub = (isa_circuit, observables, parameters)

    return pub, [ev for _, ev in observable_ideal_ev_pairs]


def create_estimator_test_data_extended(backend, preset_pass_manager, include_projectors):
    """Create a pub and ideal expectation values for it.

    The circuit will use 4 qubits and try to use an extensive list of observables to provide
    coverage.
    Due a bigger number of qubits and observables, expect longer runtimes when using it,
    especially in noisy simulations.
    """
    circuit = make_mirror_circuit_with_phases(
        backend, num_qubits=4, add_measurement=False, add_rx=False
    )

    circuit.rx(Parameter("rx_0"), 0)
    circuit.rx(Parameter("rx_1"), 1)
    circuit.ry(Parameter("ry_2"), 2)
    circuit.ry(Parameter("ry_3"), 3)
    isa_circuit = preset_pass_manager.run(circuit)

    theta = np.pi / 5
    phi = np.pi / 3
    parameters = [theta, -phi, 3 * np.pi / 4, -3 * np.pi / 4]

    sq2_half = np.sqrt(2) / 2
    r_q1 = (1 + np.sin(phi)) / 2
    y_q1 = np.sin(phi)
    l_q0 = (1 + np.sin(theta)) / 2
    z_q0 = np.cos(theta)
    x_q2 = sq2_half
    proj_q2 = (1 + sq2_half) / 2
    z0_q0 = (1 + np.cos(theta)) / 2

    observable_ideal_ev_pairs = [
        ("IIYZ", z_q0 * y_q1),  # ≈ 0.700
        ("IXII", x_q2),  # ≈ 0.707
        # Weighted linear combination:
        (
            SparsePauliOp.from_list([("IIYZ", 0.7), ("IXII", 0.5)]),
            0.7 * z_q0 * y_q1 + 0.5 * x_q2,
        ),  # ≈ 0.843
    ]

    if include_projectors:
        observable_ideal_ev_pairs.extend(
            [
                ("IIrl", r_q1 * l_q0),  # ≈ 0.741
                ("IIrZ", r_q1 * z_q0),  # ≈ 0.755
                ("I+YI", proj_q2 * y_q1),  # ≈ 0.740
                ("-IYI", proj_q2 * y_q1),  # ≈ 0.740
                ("IIY0", y_q1 * z0_q0),  # ≈ 0.783
                ("I1YI", proj_q2 * y_q1),  # ≈ 0.740
            ]
        )

    observables = ObservablesArray([obs for obs, _ in observable_ideal_ev_pairs]).apply_layout(
        isa_circuit.layout
    )

    pub = (isa_circuit, observables, parameters)

    return pub, [ev for _, ev in observable_ideal_ev_pairs]


def create_noise_model_without_noise(estimator, pub):
    """Creates a noise-model, mapping each layer to the identity (no noise)."""
    layers = estimator.find_unique_layers([pub], types="gates")

    # In a noise-less simulation we do not expect noise. So we can construct the noise_model
    # with empty noise for all layers:
    noise_model = [
        (layer, PauliLindbladMap.identity(layer.operation.num_qubits)) for layer in layers
    ]
    return noise_model


def create_local_mode_estimator(
    backend: BackendV2,
    num_randomizations: int,
    shots_per_randomization: int,
    options_overrides: dict[str, Any] = {},
) -> EstimatorV2:
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
        },
    )
    options.update(**options_overrides)

    # Increase number of shots to have better statistics:
    options.twirling.num_randomizations = num_randomizations
    options.twirling.shots_per_randomization = shots_per_randomization
    options.default_shots = num_randomizations * shots_per_randomization

    return EstimatorV2(mode=backend, options=options)
