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
from qiskit.quantum_info import Operator, PauliLindbladMap, SparsePauliOp
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

from ....utils import make_mirror_circuit_with_phases


def create_estimator_test_data_big(backend, preset_pass_manager):
    """Create a pub and ideal expectation values for it.

    The circuit will use 4 qubits and try to use an extensive list of observables to provide
    coverage.
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

    # FIXME: Composing observables from plain `Operator` instead of directly passing strings,
    # due to a bug in TREX post-processing affecting resilience levels > 0:
    # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
    # Once this is fixed, we can pass the label strings directly.
    def _obs(label):
        return SparsePauliOp.from_operator(Operator.from_label(label)).apply_layout(
            isa_circuit.layout
        )

    observable_ideal_ev_pairs: list[tuple[SparsePauliOp, float]] = [
        (_obs("IIrl"), r_q1 * l_q0),  # ≈ 0.741
        (_obs("IIrZ"), r_q1 * z_q0),  # ≈ 0.755
        (_obs("I+YI"), proj_q2 * y_q1),  # ≈ 0.740
        (_obs("-IYI"), proj_q2 * y_q1),  # ≈ 0.740
        (_obs("IIY0"), y_q1 * z0_q0),  # ≈ 0.783
        (_obs("I1YI"), proj_q2 * y_q1),  # ≈ 0.740
        (_obs("IXII"), x_q2),  # ≈ 0.707
        # Weighted linear combination:
        (
            2.0 * _obs("-IrI") - 1.0 * _obs("1IYI"),
            2.0 * proj_q2 * r_q1 - 1.0 * proj_q2 * y_q1,
        ),  # ≈ 0.854
    ]

    pub = (isa_circuit, [obs for obs, _ in observable_ideal_ev_pairs], parameters)

    return pub, [ev for _, ev in observable_ideal_ev_pairs]


def create_estimator_test_data_small(backend, preset_pass_manager):
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
        ("Irl", r_q1 * l_q0),  # ≈ 0.741
        ("XII", x_q2),  # ≈ 0.707
    ]

    # FIXME: Composing observables from plain `Operator` instead of directly passing strings,
    # due to a bug in TREX post-processing affecting resilience levels > 0:
    # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
    # Once this is fixed, we can do:
    # observables = [obs_string for obs_string, _ in observable_ideal_ev_pairs]
    observables = [
        SparsePauliOp.from_operator(Operator.from_label(obs_string)).apply_layout(
            isa_circuit.layout
        )
        for obs_string, _ in observable_ideal_ev_pairs
    ]

    pub = (isa_circuit, observables, parameters)

    return pub, [ev for _, ev in observable_ideal_ev_pairs]


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
