# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Neat class."""

import numpy as np

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.debug_tools import Neat, NeatResult

from ...ibm_test_case import IBMTestCase


class TestNeat(IBMTestCase):
    """Class for testing the Neat class."""

    def setUp(self):
        super().setUp()

        noise_strength = 0.05
        self.noise_model = NoiseModel()
        self.noise_model.add_quantum_error(depolarizing_error(noise_strength, 2), ["cx"], [0, 1])
        self.noise_model.add_quantum_error(depolarizing_error(noise_strength, 2), ["cx"], [1, 0])
        self.noise_model.add_quantum_error(depolarizing_error(noise_strength, 2), ["cx"], [1, 2])
        self.backend = AerSimulator(
            noise_model=self.noise_model, coupling_map=[[0, 1], [1, 0], [1, 2]]
        )

        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=0)

        self.c1 = QuantumCircuit(2)
        self.c1.h(0)
        self.c1.cx(0, 1)
        self.c1 = pm.run(self.c1)
        self.obs1_xx = SparsePauliOp(["XX"]).apply_layout(self.c1.layout)
        self.obs1_zi = SparsePauliOp(["ZI"]).apply_layout(self.c1.layout)

        self.c2 = QuantumCircuit(3)
        self.c2.h(0)
        self.c2.cx(0, 1)
        self.c2.cx(1, 2)
        self.c2 = pm.run(self.c2)
        self.obs2_xxx = SparsePauliOp(["XXX"]).apply_layout(self.c2.layout)
        self.obs2_zzz = SparsePauliOp(["ZZZ"]).apply_layout(self.c2.layout)
        self.obs2_ziz = SparsePauliOp(["ZIZ"]).apply_layout(self.c2.layout)

    def test_simulate_ideal(self):
        r"""Test the ``simulate`` method with ``with_noise=False``."""
        analyzer = Neat(self.backend)

        r1 = analyzer.simulate([(self.c1, self.obs1_xx)], with_noise=False)
        self.assertIsInstance(r1, NeatResult)
        self.assertEqual(r1[0].vals, 1)

        r2 = analyzer.simulate([(self.c1, [self.obs1_xx, self.obs1_zi])], with_noise=False)
        self.assertIsInstance(r2, NeatResult)
        self.assertListEqual(r2[0].vals.tolist(), [1, 0])

        pubs3 = [
            (self.c1, [self.obs1_xx, self.obs1_zi]),
            (self.c2, [self.obs2_xxx, self.obs2_zzz, self.obs2_ziz]),
        ]
        r3 = analyzer.simulate(pubs3, with_noise=False)
        self.assertIsInstance(r3, NeatResult)
        self.assertListEqual(r3[0].vals.tolist(), [1, 0])
        self.assertListEqual(r3[1].vals.tolist(), [1, 0, 1])

    def test_simulate_noisy(self):
        r"""Test the ``simulate`` method with ``with_noise=True``."""
        analyzer = Neat(self.backend, self.noise_model)

        r1 = analyzer.simulate([(self.c1, self.obs1_xx)], with_noise=True)
        self.assertIsInstance(r1, NeatResult)
        self.assertListEqual(list(r1[0].vals.shape), [])

        r2 = analyzer.simulate([(self.c1, [self.obs1_xx, self.obs1_zi])], with_noise=True)
        self.assertIsInstance(r2, NeatResult)
        self.assertListEqual(list(r2[0].vals.shape), [2])

        pubs3 = [
            (self.c1, [self.obs1_xx, self.obs1_zi]),
            (self.c2, [self.obs2_xxx, self.obs2_zzz, self.obs2_ziz]),
        ]
        r3 = analyzer.simulate(pubs3, with_noise=True)
        self.assertIsInstance(r3, NeatResult)
        self.assertListEqual(list(r3[0].vals.shape), [2])
        self.assertListEqual(list(r3[1].vals.shape), [3])

    def test_non_clifford_error(self):
        r"""Tests that ``simulate`` errors when pubs are not Clifford."""
        qc = QuantumCircuit(3)
        qc.rz(0.02, 0)
        pubs = [(qc, "ZZZ")]

        with self.assertRaisesRegex(ValueError, "non-Clifford circuit"):
            Neat(self.backend).simulate(pubs)

    def test_to_clifford(self):
        r"""Tests the ``to_clifford`` method."""
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
        transformed = Neat(self.backend).to_clifford([(qc, "ZZ")])[0]

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
