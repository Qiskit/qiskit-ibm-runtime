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

"""Tests for the debugger."""

from typing import Optional
from ddt import ddt

from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.primitives.containers import PrimitiveResult
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_aer.noise import NoiseModel
from qiskit_aer.primitives import EstimatorV2 as AerEstimator

from qiskit_ibm_runtime.debugger import Debugger, Ratio, FOM
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from ...ibm_test_case import IBMTestCase


class Prod(FOM):
    r"""
    A custom FOM used to test the compare method of the debugger.
    """

    def call(self, result1: PrimitiveResult, result2: PrimitiveResult):
        return [r1.data.evs * r2.data.evs for r1, r2 in zip(result1, result2)]


@ddt
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

        # Default seed and precision
        self.seed = 12
        self.prec = 0

    def get_result_ideal_sim(
        self,
        pubs: list[EstimatorPub],
        seed_simulator: Optional[int] = None,
        default_precision: Optional[float] = 0,
    ):
        r"""
        Does not validate pubs.
        """
        options = {"method": "stabilizer", "seed_simulator": seed_simulator or self.seed}
        estimator = AerEstimator(
            options={
                "backend_options": options,
                "default_precision": default_precision or self.prec,
            }
        )
        return estimator.run(pubs).result()

    def get_result_noisy_sim(
        self,
        pubs: list[EstimatorPub],
        noise_model: NoiseModel,
        seed_simulator: Optional[int] = None,
        default_precision: Optional[float] = 0,
    ):
        r"""
        Does not validate pubs.
        """
        options = {
            "method": "stabilizer",
            "noise_model": noise_model,
            "seed_simulator": seed_simulator or self.seed,
        }
        estimator = AerEstimator(
            options={
                "backend_options": options,
                "default_precision": default_precision or self.prec,
            }
        )
        return estimator.run(pubs).result()

    def test_compare_ideal_vs_noisy(self):
        r"""
        Test the compare method with standard inputs.
        """
        debugger = Debugger(self.backend)
        ratio = debugger.compare(self.pubs, seed_simulator=self.seed)

        ideal_result = self.get_result_ideal_sim(self.pubs)
        noisy_result = self.get_result_noisy_sim(self.pubs, self.noise_model)

        expected = Ratio(noisy_result, ideal_result)
        self.assertListEqual(ratio, expected)

    def test_compare_ideal_vs_exp(self):
        r"""
        Test the compare method when exp results are passed.
        """
        result = self.get_result_noisy_sim(self.pubs, self.noise_model)

        debugger = Debugger(self.backend)
        ratio = debugger.compare(self.pubs, "exp", "ideal_sim", result)

        expected = Ratio(result, self.get_result_ideal_sim(self.pubs))
        self.assertListEqual(ratio, expected)

    def test_compare_noisy_vs_exp(self):
        r"""
        Test the compare method when exp results are passed and compared to noisy results.
        """
        result = self.get_result_noisy_sim(self.pubs, self.noise_model)

        debugger = Debugger(self.backend)
        ratio = debugger.compare(self.pubs, "exp", "noisy_sim", result, seed_simulator=self.seed)

        expected = Ratio(result, self.get_result_noisy_sim(self.pubs, self.noise_model))
        self.assertListEqual(ratio, expected)

    def test_wrong_string(self):
        r"""
        Test the errors raised by compare when passing a wrong string.
        """
        debugger = Debugger(self.backend)

        with self.assertRaises(ValueError):
            debugger.compare(self.pubs, "expp", "ideal_sim")

    def test_custom_fom(self):
        r"""
        Test the compare method when a custom FOM is given.
        """
        debugger = Debugger(self.backend)
        prod = debugger.compare(self.pubs, seed_simulator=self.seed, fom=Prod)

        ideal_result = self.get_result_ideal_sim(self.pubs)
        noisy_result = self.get_result_noisy_sim(self.pubs, self.noise_model)

        expected = [r1.data.evs * r2.data.evs for r1, r2 in zip(ideal_result, noisy_result)]
        self.assertListEqual(prod, expected)
