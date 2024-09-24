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

from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.primitives.containers import PubResult, DataBin
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_aer.noise import NoiseModel
from qiskit_aer.primitives import EstimatorV2 as AerEstimator

from qiskit_ibm_runtime.debugger import Debugger
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from ...ibm_test_case import IBMTestCase
from ...utils import combine


class TestDebugger(IBMTestCase):
    """Class for testing the Debugger class."""

    def setUp(self):
        super().setUp()

        self.backend = FakeSherbrooke()
        self.noise_model = NoiseModel.from_backend(self.backend, thermal_relaxation=False)
        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=0)

        # A set of pubs
        c1 = QuantumCircuit(2)
        c1.h(0)
        c1.cx(0, 1)
        c1 = pm.run(c1)
        obs1 = SparsePauliOp(["ZZ", "ZI", "IZ", "XX"]).apply_layout(c1.layout)

        c2 = QuantumCircuit(3)
        c2.h(0)
        c2.cx(0, 1)
        c2.cx(1, 2)
        c2 = pm.run(c2)
        obs2 = SparsePauliOp(["ZZZ"]).apply_layout(c2.layout)

        self.pubs = [(c1, obs1), (c2, obs2)]

    def test_simulate_ideal(self, scalar, idx, op_name):
        r"""Test the ``simulate`` method with ``ideal_sim=True``."""
        debugger = Debugger(self.backend)

        result = debugger.simulate(self.pubs, ideal_sim=True)