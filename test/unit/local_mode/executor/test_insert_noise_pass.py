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

"""Tests for InsertNoisePass."""

from __future__ import annotations

import warnings
from itertools import product
from unittest import skipUnless

import numpy as np
from ddt import data, ddt, unpack
from qiskit.circuit import Barrier, QuantumCircuit
from qiskit.quantum_info import DensityMatrix, PauliLindbladMap
from qiskit.transpiler import PassManager
from qiskit.utils import optionals

from qiskit_ibm_runtime.fake_provider.executor.insert_noise_pass import POSITIONS, InsertNoisePass

from ....ibm_test_case import IBMTestCase

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator

MAP = PauliLindbladMap.from_list([("XI", 0.1)])


def _circuit_with_barrier(
    n_qubits: int, label: str, qubits: list[int] | None = None
) -> QuantumCircuit:
    """A circuit holding one labeled barrier, optionally on a qubit subset in a given order."""
    circuit = QuantumCircuit(n_qubits)
    qubits = list(range(n_qubits)) if qubits is None else qubits
    circuit.append(Barrier(len(qubits), label=label), qubits)
    return circuit


def _circuit_with_sandwich(n_qubits: int, tag: str) -> QuantumCircuit:
    """The three-barrier sandwich samplomatic emits around one dressed box."""
    circuit = QuantumCircuit(n_qubits)
    for position in POSITIONS:
        circuit.append(Barrier(n_qubits, label=f"{position}0@tag={tag}"), range(n_qubits))
    return circuit


def _structure(circuit: QuantumCircuit) -> list[tuple[str, tuple[int, ...]]]:
    """Every instruction as ``(name, qubit indices)``.

    Comparing against an expected list pins *what* was inserted, *where* in the sequence, and *which
    qubits* it acts on — none of which an instruction count would catch.
    """
    return [
        (instr.operation.name, tuple(circuit.find_bit(qubit).index for qubit in instr.qubits))
        for instr in circuit.data
    ]


def _rates(circuit: QuantumCircuit) -> list[np.ndarray]:
    """The rates of each inserted channel, in circuit order."""
    # PauliLindbladError is wrapped in QuantumChannelInstruction, which stores it as _quantum_error.
    return [
        instr.operation._quantum_error.rates  # noqa: SLF001
        for instr in circuit.data
        if instr.operation.name == "quantum_channel"
    ]


@ddt
@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestInsertNoisePass(IBMTestCase):
    """Tests for InsertNoisePass."""

    @data(*product(POSITIONS, POSITIONS))
    @unpack
    def test_noise_lands_only_at_the_requested_position(self, requested, barrier_position):
        """A channel follows the requested barrier position and no other."""
        circuit = _circuit_with_barrier(2, f"{barrier_position}0@tag=r0")
        result = PassManager([InsertNoisePass({"r0": {requested: MAP}})]).run(circuit)

        expected = [("barrier", (0, 1))]
        if requested == barrier_position:
            expected.append(("quantum_channel", (0, 1)))
        self.assertEqual(_structure(result), expected)

    def test_each_position_of_one_tag_gets_its_own_channel(self):
        """A box that both measures and resets needs a different channel at two of its barriers."""
        noise_dict = {
            "spam": {
                "M": PauliLindbladMap.from_list([("XI", 0.1)]),
                "R": PauliLindbladMap.from_list([("IX", 0.2)]),
            }
        }
        result = PassManager([InsertNoisePass(noise_dict)]).run(_circuit_with_sandwich(2, "spam"))

        # L is left bare; M and R are each followed by exactly one channel.
        self.assertEqual(
            _structure(result),
            [
                ("barrier", (0, 1)),
                ("barrier", (0, 1)),
                ("quantum_channel", (0, 1)),
                ("barrier", (0, 1)),
                ("quantum_channel", (0, 1)),
            ],
        )
        # The two maps are not interchangeable, so check each landed at its own position.
        rates = _rates(result)
        np.testing.assert_allclose(rates[0], [0.1])
        np.testing.assert_allclose(rates[1], [0.2])

    @data(
        ("R0@tag=r0", True),
        ("R0@foo=bar&tag=r0&baz=qux", True),
        ("R0@tag=r0&inject_noise=n0", True),
        ("R0@inject_noise=n0&tag=r0", True),
        ("R0_0@tag=r0", True),
        ("R1_2_3@tag=r0", True),
        ("R0@tag=other", False),
        ("R0@inject_noise=n0", False),
        ("R0", False),
        ("my_custom_barrier", False),
    )
    @unpack
    def test_tag_is_matched_across_label_shapes(self, label, expect_noise):
        """The tag is recovered from every label shape, and only a matching tag inserts noise.

        The ``&``-delimited cases are regressions: a greedy pattern captures everything after
        ``tag=`` and then silently fails to match.
        """
        result = PassManager([InsertNoisePass({"r0": {"R": MAP}})]).run(
            _circuit_with_barrier(2, label)
        )

        expected = [("barrier", (0, 1))]
        if expect_noise:
            expected.append(("quantum_channel", (0, 1)))
        self.assertEqual(_structure(result), expected)

    @data("Q", "l")
    def test_unknown_position_is_rejected(self, position):
        """An unknown position letter is a programming error, not a silent no-op."""
        with self.assertRaisesRegex(ValueError, "unknown barrier position"):
            InsertNoisePass({"r0": {position: MAP}})

    @data((1.0, 0.1), (3.0, 0.3), (0.0, 0.0))
    @unpack
    def test_noise_scale_multiplies_rates(self, noise_scale, expected_rate):
        """``noise_scale`` scales the rates and leaves the structure alone."""
        circuit = _circuit_with_barrier(2, "R0@tag=r0")
        result = PassManager([InsertNoisePass({"r0": {"R": MAP}}, noise_scale=noise_scale)]).run(
            circuit
        )

        self.assertEqual(_structure(result), [("barrier", (0, 1)), ("quantum_channel", (0, 1))])
        np.testing.assert_allclose(_rates(result)[0], [expected_rate])

    def test_an_absent_tag_is_silent_and_changes_nothing(self):
        """The pass reports nothing about coverage; that is the caller's job, not the pass's.

        A gates-only noise model legitimately leaves measurement and preparation boxes bare, so a
        tag with no entry is ordinary rather than something to report.
        """
        circuit = _circuit_with_sandwich(2, "unknown")

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = PassManager([InsertNoisePass({"r0": {"R": MAP}})]).run(circuit)

        self.assertEqual(_structure(result), _structure(circuit))

    @data(None, {})
    def test_empty_noise_model_changes_nothing(self, noise_dict):
        """``None`` and an empty dict both leave the circuit untouched."""
        circuit = _circuit_with_barrier(2, "R0@tag=r0")
        result = PassManager([InsertNoisePass(noise_dict)]).run(circuit)
        self.assertEqual(_structure(result), _structure(circuit))

    def test_channel_qubits_are_sorted_into_ascending_circuit_order(self):
        """A barrier's qargs are treated as a set: the channel lands on them in ascending order.

        The barrier here is on ``(2, 0)`` — descending — and the channel must still come out on
        ``(0, 2)``.  The barrier itself must survive exactly once; an earlier fix duplicated it.
        """
        circuit = _circuit_with_barrier(3, "R0@tag=r0", qubits=[2, 0])
        result = PassManager([InsertNoisePass({"r0": {"R": MAP}})]).run(circuit)

        self.assertEqual(_structure(result), [("barrier", (2, 0)), ("quantum_channel", (0, 2))])

    @data(
        # Two-qubit map on a descending barrier — the example in the ``noise_dict`` docstring.
        (3, [2, 0], [("IX", 0.3)], [0.3, 0.0, 0.0]),
        (3, [2, 0], [("XI", 0.3)], [0.0, 0.0, 0.3]),
        # Three-qubit map on a scattered, unsorted barrier.
        (4, [3, 0, 1], [("IIX", 0.20), ("IXI", 0.10), ("XII", 0.05)], [0.20, 0.10, 0.0, 0.05]),
    )
    @unpack
    def test_simulated_rates_land_on_the_intended_physical_qubits(
        self, num_qubits, qubits, generators, rate_per_qubit
    ):
        """Simulate to confirm the qubit mapping end to end, not just the instruction's qargs.

        Rates are indexed by the barrier's qubits sorted ascending, so for a barrier on
        ``[3, 0, 1]`` map index 0 is qubit 0, index 1 is qubit 1 and index 2 is qubit 3.
        """
        circuit = _circuit_with_barrier(num_qubits, "R0@tag=r0", qubits=qubits)
        noise_dict = {"r0": {"R": PauliLindbladMap.from_list(generators)}}
        noisy = PassManager([InsertNoisePass(noise_dict)]).run(circuit)
        noisy.save_density_matrix()

        result = AerSimulator(method="density_matrix").run(noisy).result()
        density_matrix = DensityMatrix(result.data(0)["density_matrix"])

        expected_p1 = (1 - np.exp(-2 * np.array(rate_per_qubit))) / 2
        actual_p1 = [density_matrix.probabilities([q])[1] for q in range(num_qubits)]
        np.testing.assert_allclose(actual_p1, expected_p1, atol=1e-10)
