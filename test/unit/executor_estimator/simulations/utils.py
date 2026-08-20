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
from qiskit.primitives import EstimatorPub
from qiskit.quantum_info import (
    Operator,
    PauliLindbladMap,
    SparseObservable,
    SparsePauliOp,
    Statevector,
)
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
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


def create_estimator_test_data_with_groupings(backend, preset_pass_manager, measure_mitigation):
    """Create a pub and ideal expectation values for it.

    The circuit will use 3 qubits and only a subset of observable combinations.
    """
    circuit = make_mirror_circuit_with_phases(
        backend, num_qubits=3, add_measurement=False, add_rx=False
    )

    pubs_list = []
    expected_evs_list = []
    groupings_list = []

    circuit.rx(Parameter("rx_0"), 0)
    circuit.rx(Parameter("rx_1"), 1)
    circuit.ry(Parameter("ry_2"), 2)
    isa_circuit = preset_pass_manager.run(circuit)

    theta = np.pi / 5
    phi = -np.pi / 3
    parameters = [theta, phi, 3 * np.pi / 4]

    y_q0 = -np.sin(theta)
    y_q1 = -np.sin(phi)
    z_q0 = np.cos(theta)
    z_q1 = np.cos(phi)
    r_q1 = (1 - np.sin(phi)) / 2
    l_q0 = (1 + np.sin(theta)) / 2
    x_q2 = np.sqrt(2) / 2

    observables = [SparsePauliOp("IYZ"), SparsePauliOp("XII")]
    evs = [y_q1 * z_q0, x_q2]
    groupings = [{"IYZ": 0}, {"XII": 0}]

    pub = (isa_circuit, observables, parameters)
    pubs_list.append(pub)
    expected_evs_list.append(evs)
    groupings_list.append(groupings)

    c_IYI, c_IYY, c_IZI = 1.0, 2.0, 3.0
    evs = [c_IYI * y_q1 + c_IYY * y_q1 * y_q0 + c_IZI * z_q1]

    # IYI and IYY share a measurement basis (Y on qubit 1) → group 0.
    # IZI is independent → group 1.
    observables = [SparsePauliOp.from_list([("IYI", c_IYI), ("IYY", c_IYY), ("IZI", c_IZI)])]
    groupings = [{"IYI": 0, "IYY": 0, "IZI": 1}]

    pub = (isa_circuit, observables, parameters)
    pubs_list.append(pub)
    expected_evs_list.append(evs)
    groupings_list.append(groupings)

    if not measure_mitigation:
        observables = [SparseObservable("Irl")]
        evs = [r_q1 * l_q0]
        groupings = [{"Irl": 0}]

        pub = (isa_circuit, observables, parameters)
        pubs_list.append(pub)
        expected_evs_list.append(evs)
        groupings_list.append(groupings)

    pubs_list = [EstimatorPub.coerce(pub) for pub in pubs_list]

    return pubs_list, expected_evs_list, groupings_list


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
    layers = estimator.find_unique_layers([pub], types="gates")

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
    observables: list[dict[str, float]],
    circuit: QuantumCircuit,
    parameters: list[float],
    num_randomizations: int,
    shots_per_randomization: int,
    term_group_indices: list[dict[str, int]],
) -> npt.NDArray[np.float64]:
    """Compute the theoretical standard error of the mean for each observable.

    Pauli terms of each observable are partitioned into measurement groups by the
    caller via ``term_group_indices``. Within each group all terms share the same
    shot data, so their combined per-shot value is
    ``x_group = Σ_k c_k · eigenvalue(P_k, shot)``. The group variance
    ``Var[x_group] = ⟨(Σ_k c_k P_k)²⟩ − ⟨Σ_k c_k P_k⟩²`` is computed from an
    exact statevector simulation. Groups use independent shot batches, so their
    variances add independently.

    Returns ``sqrt(Σ_groups Var_group / N)`` where
    ``N = num_randomizations × shots_per_randomization``.

    Args:
        observables: List of observables, each as a ``{pauli_label: coefficient}`` dict
            (e.g. from ``pub.observables.tolist()``).
        circuit: The ISA circuit to simulate (parameters not yet bound).
        parameters: Parameter values to bind, in the order of ``circuit.parameters``.
        num_randomizations: Number of twirl randomizations (R).
        shots_per_randomization: Number of shots per randomization (S). N = R × S.
        term_group_indices: One ``{pauli_label: group_index}`` dict per observable.
            Terms with the same group index share one shot batch; terms with different
            indices are independent. Labels must match those in the corresponding
            observable dict.

    Returns:
        Array of shape ``(len(observables),)`` containing the theoretical SEM for
        each observable.
    """
    bound_circuit = circuit.assign_parameters(dict(zip(circuit.parameters, parameters)))
    sv = Statevector(bound_circuit)
    n_total = num_randomizations * shots_per_randomization

    num_qubits = bound_circuit.num_qubits
    sems = np.empty(len(observables), dtype=float)
    for i, obs in enumerate(observables):
        groups: dict[int, list[tuple[str, float]]] = defaultdict(list)
        for term, coeff in obs.items():
            group_idx = term_group_indices[i][term]
            groups[group_idx].append((term, coeff))

        # Sum variance contributions across independent measurement groups.
        total_var = 0.0
        for terms_in_group in groups.values():
            # Build via SparseObservable to handle both plain Pauli strings and
            # projector-bit labels (e.g. "Irl"), then convert to SparsePauliOp
            # so Statevector.expectation_value can consume it.
            group_so = SparseObservable.from_list(
                [(term, float(coeff)) for term, coeff in terms_in_group],
                num_qubits=num_qubits,
            ).as_paulis()
            group_op = SparsePauliOp.from_sparse_list(
                group_so.to_sparse_list(), num_qubits=num_qubits
            )
            ev_g = sv.expectation_value(group_op).real
            ev_g_sq = sv.expectation_value(group_op @ group_op).real
            total_var += max(ev_g_sq - ev_g**2, 0.0)

        sems[i] = np.sqrt(total_var / n_total)

    return sems
