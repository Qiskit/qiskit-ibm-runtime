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

"""Tests for Debugger class."""

import numpy as np
import ddt

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime.debugger import Debugger
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from ...ibm_test_case import IBMTestCase
from ...utils import combine


class TestDebugger(IBMTestCase):
    """Class for testing the Debugger class."""

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
        debugger = Debugger(self.backend)

        r1 = debugger.simulate([(self.c1, self.obs1_xx)], with_noise=False)
        self.assertEqual(r1[0].vals, 1)

        r2 = debugger.simulate([(self.c1, [self.obs1_xx, self.obs1_zi])], with_noise=False)
        self.assertListEqual(r2[0].vals.tolist(), [1, 0])

        r3 = debugger.simulate(
            [
                (self.c1, [self.obs1_xx, self.obs1_zi]),
                (self.c2, [self.obs2_xxx, self.obs2_zzz, self.obs2_ziz]),
            ],
            with_noise=False,
        )
        self.assertListEqual(r3[0].vals.tolist(), [1, 0])
        self.assertListEqual(r3[1].vals.tolist(), [1, 0, 1])

    def test_simulate_noisy(self):
        r"""Test the ``simulate`` method with ``with_noise=True``."""
        debugger = Debugger(self.backend, self.noise_model)

        r1 = debugger.simulate([(self.c1, self.obs1_xx)], with_noise=True)
        self.assertListEqual(list(r1[0].vals.shape), [])

        r2 = debugger.simulate([(self.c1, [self.obs1_xx, self.obs1_zi])], with_noise=True)
        self.assertListEqual(list(r2[0].vals.shape), [2])

        r3 = debugger.simulate(
            [
                (self.c1, [self.obs1_xx, self.obs1_zi]),
                (self.c2, [self.obs2_xxx, self.obs2_zzz, self.obs2_ziz]),
            ],
            with_noise=False,
        )
        self.assertListEqual(list(r3[0].vals.shape), [2])
        self.assertListEqual(list(r3[1].vals.shape), [3])
