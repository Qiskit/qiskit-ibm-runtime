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

"""Unit tests."""

from itertools import islice, product
from unittest import skipUnless

from ddt import data, ddt, unpack
from qiskit.circuit import QuantumCircuit
from qiskit.primitives.containers.bit_array import BitArray
from qiskit.quantum_info import PauliLindbladMap
from qiskit.utils import optionals
from samplomatic import Tag, Twirl
from samplomatic.builders.build import build

from qiskit_ibm_runtime.fake_provider.backends.fez import FakeFez
from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMTestCase

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator

    from qiskit_ibm_runtime.aer_executor import AerExecutor


def _batched(iterable, n, *, strict=False):
    # _batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    iterator = iter(iterable)
    while batch := tuple(islice(iterator, n)):
        if strict and len(batch) != n:
            raise ValueError("_batched(): incomplete batch")
        yield batch


def _circ_a():
    num_qubits = 2
    active_qubits = list(range(num_qubits))

    qc_boxed = QuantumCircuit(num_qubits, num_qubits)
    with qc_boxed.box(
        annotations=[
            Twirl(dressing="left"),
            Tag(ref="r0"),
        ]
    ):  # pyright: ignore[reportGeneralTypeIssues]
        for edge in _batched(active_qubits, 2):
            if len(edge) == 2:
                qc_boxed.cz(*edge)

    with qc_boxed.box(annotations=[Twirl(dressing="right")]):
        qc_boxed.noop([0, 1])
    return qc_boxed, active_qubits


def _circ_b():
    fez_backend = FakeFez()
    coupling_map = fez_backend.coupling_map
    active_qubits = list(range(fez_backend.num_qubits))

    qc_boxed = QuantumCircuit(fez_backend.num_qubits, fez_backend.num_qubits)
    with qc_boxed.box(
        annotations=[
            Twirl(dressing="left"),
            Tag(ref="r0"),
        ]
    ):  # pyright: ignore[reportGeneralTypeIssues]
        for edge in _batched(active_qubits, 2):
            if edge in coupling_map:
                qc_boxed.cz(*edge)
            else:
                qc_boxed.z(edge)

    with qc_boxed.box(annotations=[Twirl(dressing="right")]):
        qc_boxed.noop(active_qubits)

    return qc_boxed, active_qubits


@ddt
@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestNoisySimulation(IBMTestCase):
    """Test noisy simulation."""

    @data(*product([True, False], ["a", "b"]))
    @unpack
    def test_noisy_simulation(self, noise, case):
        """Test noisy simulation."""
        if case == "a":
            qc_boxed, active_qubits = _circ_a()
        elif case == "b":
            qc_boxed, active_qubits = _circ_b()
        else:
            raise ValueError("...")

        qc_boxed.measure(active_qubits, active_qubits)

        template_circuit, samplex = build(qc_boxed)

        self.assertGreater(template_circuit.count_ops().get("rz", 0), 0)

        shots_per_twirl = 1024
        num_twirls = 1
        num_shots_tot = shots_per_twirl * num_twirls

        # Build a QuantumProgram using a SamplexItem
        program = QuantumProgram(shots=shots_per_twirl)
        program.append_samplex_item(
            template_circuit,
            samplex=samplex,
            shape=(num_twirls,),
        )

        def _xi(i: int, n: int = len(active_qubits)) -> str:
            ll = ["I"] * n
            ll[i] = "X"
            return "".join(reversed(ll))

        if noise:
            noise_dict = {
                "r0": PauliLindbladMap.from_list(
                    [(_xi(i), 1e-1) for i in range(len(active_qubits))]
                ),
            }
        else:
            noise_dict = None

        # Run via AerExecutor
        executor = AerExecutor(AerSimulator(method="stabilizer"), noise_dict=noise_dict)
        job = executor.run(program)
        result = job.result()

        self.assertEqual(len(result), 1)

        ba_c = BitArray.from_bool_array(result[0]["c"])
        cts = ba_c.get_counts()
        if noise:
            self.assertGreater(num_shots_tot, cts.get("0" * len(active_qubits), 0))
        else:
            self.assertEqual(num_shots_tot, cts.get("0" * len(active_qubits), 0))
