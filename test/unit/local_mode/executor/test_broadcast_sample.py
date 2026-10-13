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

"""Tests for ``broadcast_sample``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from samplomatic.builders.build import build
from samplomatic.transpiler import generate_boxing_pass_manager

from qiskit_ibm_runtime.fake_provider.backends.fez import FakeFez
from qiskit_ibm_runtime.fake_provider.executor.broadcast_sample import broadcast_sample
from qiskit_ibm_runtime.quantum_program import QuantumProgram

if TYPE_CHECKING:
    from qiskit_ibm_runtime.quantum_program import SamplexItem


@pytest.fixture
def cx_item() -> SamplexItem:
    """Return a SamplexItem for a Pauli-twirled CX circuit (no free parameters)."""
    qc = QuantumCircuit(2, 2)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    pm = generate_preset_pass_manager(
        backend=FakeFez(), initial_layout=[17, 27], optimization_level=0
    )
    pm.post_scheduling = generate_boxing_pass_manager()
    transpiled = pm.run(qc)
    template_circuit, samplex = build(transpiled)
    program = QuantumProgram(shots=64)
    program.append_samplex_item(template_circuit, samplex=samplex, shape=(3, 5))
    return program.items[0]


@pytest.fixture
def mixed_axes_item() -> SamplexItem:
    """Return a SamplexItem with mixed broadcast/randomization axes: shape (r0, 2, 2, r1)."""
    theta = Parameter("theta")
    phi = Parameter("phi")
    qc = QuantumCircuit(2, 2)
    qc.rx(theta, 0)
    qc.cx(0, 1)
    qc.rx(phi, 1)
    qc.measure([0, 1], [0, 1])
    pm = generate_preset_pass_manager(
        backend=FakeFez(), initial_layout=[17, 27], optimization_level=0
    )
    pm.post_scheduling = generate_boxing_pass_manager()
    transpiled = pm.run(qc)
    template_circuit, samplex = build(transpiled)
    # parameters sorted alphabetically: [phi, theta]
    param_values = np.array([[[0.0, 0.0], [np.pi, 0.0]], [[0.0, np.pi], [np.pi, np.pi]]]).reshape(
        (2, 2, 1, 2)
    )
    program = QuantumProgram(shots=64)
    program.append_samplex_item(
        template_circuit,
        samplex=samplex,
        samplex_arguments={"parameter_values": param_values},
        shape=(3, 2, 2, 4),
    )
    return program.items[0]


class TestBroadcastSample:
    """Tests for ``broadcast_sample``."""

    def test_broadcast_sample_no_broadcast_axes(self, cx_item: SamplexItem) -> None:
        """All axes are randomization axes: output shape matches the requested shape."""
        shape = cx_item.shape  # (3, 5)
        rng = np.random.default_rng(42)

        result = broadcast_sample(cx_item.samplex, cx_item.samplex_arguments, shape, rng)

        assert isinstance(result, dict)
        assert len(result) > 0
        for key, val in result.items():
            assert val.shape[: len(shape)] == shape

    def test_broadcast_sample_output_keys(self, cx_item: SamplexItem) -> None:
        """Output contains 'parameter_values' and at least one 'measurement_flips.*' key."""
        rng = np.random.default_rng(0)

        result = broadcast_sample(cx_item.samplex, cx_item.samplex_arguments, cx_item.shape, rng)

        assert "parameter_values" in result

        flip_keys = [k for k in result if k.startswith("measurement_flips.")]
        assert len(flip_keys) > 0

    def test_broadcast_sample_all_broadcast_axes(self, mixed_axes_item: SamplexItem) -> None:
        """Broadcast axes produce the correct leading shape."""
        shape = mixed_axes_item.shape  # (3, 2, 2, 4)
        rng = np.random.default_rng(7)

        result = broadcast_sample(
            mixed_axes_item.samplex, mixed_axes_item.samplex_arguments, shape, rng
        )

        for key, val in result.items():
            assert val.shape[: len(shape)] == shape

    def test_broadcast_sample_rng_reproducible(self, cx_item: SamplexItem) -> None:
        """Same RNG seed produces identical results."""
        r1 = broadcast_sample(
            cx_item.samplex, cx_item.samplex_arguments, cx_item.shape, np.random.default_rng(1)
        )
        r2 = broadcast_sample(
            cx_item.samplex, cx_item.samplex_arguments, cx_item.shape, np.random.default_rng(1)
        )

        for key in r1:
            np.testing.assert_array_equal(r1[key], r2[key], err_msg=f"Mismatch in '{key}'")
