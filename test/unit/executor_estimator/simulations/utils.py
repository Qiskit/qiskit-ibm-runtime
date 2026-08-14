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
from qiskit.primitives.containers.estimator_pub import ObservablesArray
from qiskit.quantum_info import PauliLindbladMap
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

from ....utils import make_mirror_circuit_with_phases


def create_estimator_test_data(backend, preset_pass_manager):
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
        ({"IYZ": 1.0}, y_q1 * z_q0),  # ≈ 0.741
        ({"Irl": 1.0}, r_q1 * l_q0),  # ≈ 0.755
        ({"XII": 1.0}, x_q2),  # ≈ 0.740
    ]

    observables = ObservablesArray([obs for obs, _ in observable_ideal_ev_pairs])
    isa_observables = observables.apply_layout(isa_circuit.layout)
    pub = (isa_circuit, isa_observables, parameters)

    ideal_evs = [evs for _, evs in observable_ideal_ev_pairs]

    return pub, ideal_evs


def create_estimator_test_data_extended(backend, preset_pass_manager):
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
        ({"IIrl": 1.0}, r_q1 * l_q0),  # ≈ 0.741
        ({"IIrZ": 1.0}, r_q1 * z_q0),  # ≈ 0.755
        ({"I+YI": 1.0}, proj_q2 * y_q1),  # ≈ 0.740
        ({"-IYI": 1.0}, proj_q2 * y_q1),  # ≈ 0.740
        ({"IIY0": 1.0}, y_q1 * z0_q0),  # ≈ 0.783
        ({"I1YI": 1.0}, proj_q2 * y_q1),  # ≈ 0.740
        ({"IXII": 1.0}, x_q2),  # ≈ 0.707
        # Weighted linear combination:
        (
            {"-IrI": 2.0, "1IYI": -1.0},
            2.0 * proj_q2 * r_q1 - 1.0 * proj_q2 * y_q1,
        ),  # ≈ 0.854
    ]

    observables = ObservablesArray([obs for obs, _ in observable_ideal_ev_pairs])
    isa_observables = observables.apply_layout(isa_circuit.layout)
    pub = (isa_circuit, isa_observables, parameters)

    ideal_evs = [evs for _, evs in observable_ideal_ev_pairs]

    return pub, ideal_evs


def create_noise_model_without_noise(estimator, pub):
    """Creates a noise-model, mapping each layer to the identity (no noise)."""
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

    return noise_model


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
        },
    )

    # Increase number of shots to have better statistics:
    options.twirling.num_randomizations = 100
    options.twirling.shots_per_randomization = 200
    options.default_shots = 100 * 200

    return EstimatorV2(mode=backend, options=options)
