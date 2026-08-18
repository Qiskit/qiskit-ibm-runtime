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

from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator, Pauli, PauliLindbladMap, SparsePauliOp, Statevector
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.decoders.executor_estimator.utils import identify_measure_basis
from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.executor_estimator.utils import get_pauli_basis
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions

from ....utils import make_mirror_circuit_with_phases

if TYPE_CHECKING:
    from typing import Any

    import numpy.typing as npt
    from qiskit.circuit import QuantumCircuit
    from qiskit.providers import BackendV2


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


def create_estimator_test_data_statistical(backend, preset_pass_manager):
    """Create pubs and ideal expectation values for statistical accuracy tests.

    Returns two PUBs using the same 3-qubit circuit (rx(θ)|0⟩ ⊗ rx(-φ)|0⟩ ⊗ ry(3π/4)|0⟩):

    **PUB 0** — three single-Pauli-string observables (each decomposes to exactly one term,
    so each observable maps to a single measurement config). The per-shot variance is
    simply ``1 - μ²`` and ``compute_sem_theoretical`` is exact for these.

    **PUB 1** — one multi-term observable ``1·IYI + 2·IYY + 3·IZI``:

    * ``IYI`` and ``IYY`` commute → share the same ``IYY`` measurement config → their
      combined per-shot value ``y₁ + 2·y₀y₁ = y₁(1 + 2y₀)`` is measured from the
      *same shots*, so cross-covariances contribute to the group variance.
    * ``IZI`` anticommutes with both ``IYI`` and ``IYY`` → gets its own independent
      measurement config.

    This design guarantees a predictable two-group structure regardless of iteration
    order, exercising the cross-covariance correction in the post-processor.

    Args:
        backend: The backend to use for transpilation.
        preset_pass_manager: The pass manager to use for transpilation.

    Returns:
        Tuple of ``(pubs, ideal_evs_list)`` where ``pubs`` is a list of two PUBs and
        ``ideal_evs_list[i]`` is the list of ideal expectation values for ``pubs[i]``.
    """
    circuit = make_mirror_circuit_with_phases(
        backend, num_qubits=3, layers=1, add_measurement=False, add_rx=False
    )
    circuit.rx(Parameter("rx_0"), 0)
    circuit.rx(Parameter("rx_1"), 1)
    circuit.ry(Parameter("ry_2"), 2)
    isa_circuit = preset_pass_manager.run(circuit)

    theta = np.pi / 5
    phi = np.pi / 3
    parameters = [theta, -phi, 3 * np.pi / 4]

    # Per-qubit ideal expectation values:
    #   q0: rx(theta)|0>  →  <Y> = -sin(θ),  <Z> = cos(θ)
    #   q1: rx(-phi)|0>   →  <Y> =  sin(φ),  <Z> = cos(φ)
    #   q2: ry(3π/4)|0>   →  <X> = sin(3π/4) = √2/2
    yq0 = -np.sin(theta)
    yq1 = np.sin(phi)
    zq0 = np.cos(theta)
    zq1 = np.cos(phi)
    xq2 = np.sqrt(2) / 2

    # --- PUB 0: single-Pauli-string observables (one term each, one config each) ---
    single_term_pairs = [
        ("IYZ", yq1 * zq0),  # Y on q1, Z on q0         ≈  0.701
        ("IZI", zq1),  # Z on q1                  ≈  0.500
        ("XII", xq2),  # X on q2                  ≈  0.707
    ]

    # FIXME: Composing observables from plain `Operator` instead of directly passing strings,
    # due to a bug in TREX post-processing affecting resilience levels > 0:
    # https://github.com/Qiskit/qiskit-ibm-runtime/issues/3225
    # Once this is fixed, we can pass the label strings directly.
    single_term_obs = [
        SparsePauliOp.from_operator(Operator.from_label(label)).apply_layout(isa_circuit.layout)
        for label, _ in single_term_pairs
    ]
    pub0 = (isa_circuit, single_term_obs, parameters)
    ideal_evs0 = [ev for _, ev in single_term_pairs]

    # --- PUB 1: multi-term observable 1·IYI + 2·IYY + 3·IZI ---
    #
    # Decomposition and grouping:
    #   IYI (c=1) and IYY (c=2) both have Y on q1 → commute → share IYY basis (config 0)
    #   IZI (c=3) has Z on q1, anticommutes with IYI and IYY → own IZI basis (config 1)
    #
    # Config-0 combined per-shot value:
    #   x₀ = 1·y₁ + 2·y₁·y₀  =  y₁·(1 + 2·y₀)
    #   where y₀ = Y₀-outcome ∈ {±1}, y₁ = Y₁-outcome ∈ {±1}
    #   E[x₀]   = ⟨Y_q1⟩·(1 + 2·⟨Y_q0⟩)  =  yq1·(1 + 2·yq0)
    #   E[x₀²]  = E[(1+2y₀)²]              =  5 + 4·yq0   (since y₁²=1)
    #   Var[x₀] = E[x₀²] − E[x₀]²
    #
    # Config-1 combined per-shot value:
    #   x₁ = 3·z₁   where z₁ = Z₁-outcome ∈ {±1}
    #   Var[x₁] = 9·(1 − zq1²)
    c_IYI, c_IYY, c_IZI = 1.0, 2.0, 3.0
    ev_multi = c_IYI * yq1 + c_IYY * yq1 * yq0 + c_IZI * zq1

    multi_term_obs = (
        c_IYI * SparsePauliOp.from_operator(Operator.from_label("IYI"))
        + c_IYY * SparsePauliOp.from_operator(Operator.from_label("IYY"))
        + c_IZI * SparsePauliOp.from_operator(Operator.from_label("IZI"))
    ).apply_layout(isa_circuit.layout)

    pub1 = (isa_circuit, [multi_term_obs], parameters)
    ideal_evs1 = [ev_multi]

    return [pub0, pub1], [ideal_evs0, ideal_evs1]


def create_estimator_test_data_extended(backend, preset_pass_manager):
    """Create a pub and ideal expectation values for it.

    The circuit will use 4 qubits and try to use an extensive list of observables to provide
    coverage.
    Due a bigger number of qubits and observables, expect longer runtimes when using it,
    especially in noisy simulations.
    """
    circuit = make_mirror_circuit_with_phases(
        backend, num_qubits=4, layers=1, add_measurement=False, add_rx=False
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


def compute_sem_theoretical(
    observables: list[SparsePauliOp],
    circuit: QuantumCircuit,
    parameters: list[float],
    num_randomizations: int,
    shots_per_randomization: int,
) -> npt.NDArray[np.float64]:
    """Compute the theoretical standard error of the mean for each observable.

    Mirrors the post-processor's variance calculation exactly: Pauli terms of each
    observable are grouped by measurement basis using ``identify_measure_basis`` (the
    same function called by the post-processor). Within each group, all terms share
    the same shot data, so their combined per-shot value is
    ``x_group = Σ_k c_k · eigenvalue(P_k, shot)``. The group variance
    ``Var[x_group] = ⟨(Σ_k c_k P_k)²⟩ − ⟨Σ_k c_k P_k⟩²`` is computed from an
    exact statevector simulation. Groups with different bases use independent shot
    batches, so their variances add independently.

    Returns ``sqrt(Σ_groups Var_group / N)`` where
    ``N = num_randomizations × shots_per_randomization``.

    A normal approximation for the estimator output is justified by the CLT: with
    ``num_randomizations ≥ 100`` and bounded shot eigenvalues (``±1`` for Paulis),
    the sample mean converges rapidly to a Gaussian.

    Args:
        observables: List of observables to compute SEMs for. Must be
            ``SparsePauliOp`` instances whose Pauli decomposition uses only
            standard ``I, X, Y, Z`` characters.
        circuit: The ISA circuit to simulate (parameters bound via layout but not
            yet assigned values).
        parameters: Parameter values to bind, in the order of ``circuit.parameters``.
        num_randomizations: Number of twirl randomizations (R).
        shots_per_randomization: Number of shots per randomization (S). N = R × S.

    Returns:
        Array of shape ``(len(observables),)`` containing the theoretical SEM for
        each observable.
    """
    from qiskit.primitives.containers.estimator_pub import ObservablesArray

    bound_circuit = circuit.assign_parameters(dict(zip(circuit.parameters, parameters)))
    sv = Statevector(bound_circuit)
    n_total = num_randomizations * shots_per_randomization

    sems = np.empty(len(observables), dtype=float)
    for i, obs in enumerate(observables):
        obs_dict = ObservablesArray([obs])[0]

        # Group terms by measurement basis, exactly as the post-processor does.
        basis_labels: list[str] = []
        for term in obs_dict:
            b = get_pauli_basis(term)
            if b not in basis_labels:
                basis_labels.append(b)
        param_basis_list = [(Pauli(b), idx) for idx, b in enumerate(basis_labels)]

        groups: dict[int, list[tuple[str, float]]] = defaultdict(list)
        for term, coeff in obs_dict.items():
            config_idx = identify_measure_basis(Pauli(get_pauli_basis(term)), param_basis_list)
            groups[config_idx].append((term, coeff))

        # Sum variance contributions across independent measurement groups.
        total_var = 0.0
        for terms_in_group in groups.values():
            group_op = sum(float(coeff) * SparsePauliOp(term) for term, coeff in terms_in_group)
            ev_g = sv.expectation_value(group_op).real
            ev_g_sq = sv.expectation_value(group_op @ group_op).real
            total_var += max(ev_g_sq - ev_g**2, 0.0)

        sems[i] = np.sqrt(total_var / n_total)

    return sems
