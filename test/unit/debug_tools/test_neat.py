# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Neat class."""

from unittest import skipUnless

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.utils.optionals import HAS_AER

from qiskit_ibm_runtime.debug_tools import Neat, NeatResult
from qiskit_ibm_runtime.fake_provider import FakeVigoV2

from ...ibm_test_case import IBMTestCase

if HAS_AER:
    from qiskit_aer.noise import NoiseModel, depolarizing_error


def transpiled_circuits(backend):
    """Return two GHZ circuits transpiled for `backend`, and observables laid out for them.

    The first circuit acts on two qubits, the second one on three.
    """
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)

    c1 = QuantumCircuit(2)
    c1.h(0)
    c1.cx(0, 1)
    c1 = pass_manager.run(c1)
    obs1_xx = SparsePauliOp(["XX"]).apply_layout(c1.layout)
    obs1_zi = SparsePauliOp(["ZI"]).apply_layout(c1.layout)

    c2 = QuantumCircuit(3)
    c2.h(0)
    c2.cx(0, 1)
    c2.cx(1, 2)
    c2 = pass_manager.run(c2)
    obs2_xxx = SparsePauliOp(["XXX"]).apply_layout(c2.layout)
    obs2_zzz = SparsePauliOp(["ZZZ"]).apply_layout(c2.layout)
    obs2_ziz = SparsePauliOp(["ZIZ"]).apply_layout(c2.layout)

    return c1, obs1_xx, obs1_zi, c2, obs2_xxx, obs2_zzz, obs2_ziz


@skipUnless(condition=HAS_AER, reason="qiskit-aer is required to run this test")
class TestNeat(IBMTestCase):
    """Class for testing the Neat class."""

    def test_ideal_sim(self):
        """Test the ``ideal_sim`` method."""
        backend = FakeVigoV2()
        c1, obs1_xx, obs1_zi, c2, obs2_xxx, obs2_zzz, obs2_ziz = transpiled_circuits(backend)

        analyzer = Neat(backend)

        r1 = analyzer.ideal_sim([(c1, obs1_xx)])
        self.assertIsInstance(r1, NeatResult)
        self.assertEqual(r1[0].vals, 1)

        r2 = analyzer.ideal_sim([(c1, [obs1_xx, obs1_zi])])
        self.assertIsInstance(r2, NeatResult)
        self.assertListEqual(r2[0].vals.tolist(), [1, 0])

        pubs3 = [
            (c1, [obs1_xx, obs1_zi]),
            (c2, [obs2_xxx, obs2_zzz, obs2_ziz]),
        ]
        r3 = analyzer.ideal_sim(pubs3)
        self.assertIsInstance(r3, NeatResult)
        self.assertListEqual(r3[0].vals.tolist(), [1, 0])
        self.assertListEqual(r3[1].vals.tolist(), [1, 0, 1])

    def test_noisy_sim(self):
        """Test the ``noisy_sim`` method."""
        backend = FakeVigoV2()
        c1, obs1_xx, obs1_zi, c2, obs2_xxx, obs2_zzz, obs2_ziz = transpiled_circuits(backend)

        noise_model = NoiseModel()
        noise_model.add_quantum_error(depolarizing_error(0, 2), ["cx"], [0, 1])

        analyzer = Neat(backend, noise_model)

        r1 = analyzer.noisy_sim([(c1, obs1_xx)])
        self.assertIsInstance(r1, NeatResult)
        self.assertListEqual(list(r1[0].vals.shape), [])

        r2 = analyzer.noisy_sim([(c1, [obs1_xx, obs1_zi])])
        self.assertIsInstance(r2, NeatResult)
        self.assertListEqual(list(r2[0].vals.shape), [2])

        pubs3 = [
            (c1, [obs1_xx, obs1_zi]),
            (c2, [obs2_xxx, obs2_zzz, obs2_ziz]),
        ]
        r3 = analyzer.noisy_sim(pubs3)
        self.assertIsInstance(r3, NeatResult)
        self.assertListEqual(list(r3[0].vals.shape), [2])
        self.assertListEqual(list(r3[1].vals.shape), [3])

    def test_non_clifford_error(self):
        """Tests ``_simulate`` erroring when pubs are not Clifford if not ``cliffordize`."""
        analyzer = Neat(FakeVigoV2())

        qc = QuantumCircuit(3)
        qc.rz(0.02, 0)
        pubs = [(qc, "ZZZ")]

        with self.assertRaisesRegex(ValueError, "Couldn't run"):
            analyzer.ideal_sim(pubs)

        with self.assertRaisesRegex(ValueError, "Couldn't run."):
            analyzer.noisy_sim(pubs)

        r1 = analyzer.ideal_sim(pubs, cliffordize=True)
        self.assertIsInstance(r1, NeatResult)
        self.assertEqual(r1[0].vals, 1)

        r2 = analyzer.noisy_sim(pubs, cliffordize=True)
        self.assertIsInstance(r2, NeatResult)
        self.assertEqual(r2[0].vals, 1)

    def test_to_clifford(self):
        """Tests the ``to_clifford`` method."""
        qc = QuantumCircuit(2, 2)
        qc.id(0)
        qc.sx(0)
        qc.barrier()
        qc.measure(0, 1)
        qc.rz(0, 0)
        qc.rz(np.pi / 2 - 0.1, 0)
        qc.rz(np.pi, 0)
        qc.rz(3 * np.pi / 2 + 0.1, 1)
        qc.cx(0, 1)
        transformed = Neat(FakeVigoV2()).to_clifford([(qc, "ZZ")])[0]

        expected = QuantumCircuit(2, 2)
        expected.id(0)
        expected.sx(0)
        expected.barrier()
        expected.measure(0, 1)
        expected.rz(0, 0)
        expected.rz(np.pi / 2, 0)
        expected.rz(np.pi, 0)
        expected.rz(3 * np.pi / 2, 1)
        expected.cx(0, 1)

        self.assertEqual(transformed.circuit, expected)
