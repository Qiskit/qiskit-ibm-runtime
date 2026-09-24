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

"""Tests for client-side Sampler."""

import numpy as np
from ddt import data, ddt
from qiskit.primitives import PrimitiveResult
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_sampler import Sampler
from qiskit_ibm_runtime.options_models import SamplerOptions

from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import make_mirror_circuit_with_phases


@ddt
class TestSampler(IBMIntegrationTestCase):
    """Test client-side Sampler."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = self.service.backend(self.dependencies.qpu)

        self.pm = generate_preset_pass_manager(optimization_level=1, target=self.backend.target)

    @data(True, False)
    def test_sampler(self, twirling):
        """Test sampler by submitting a couple of parametric circuits."""
        circuit = make_mirror_circuit_with_phases(self.backend)
        isa_circuit = self.pm.run(circuit)

        shapes = [(5, 4), (3,)]
        num_parameters = isa_circuit.num_parameters
        pubs = [
            (isa_circuit.copy(), np.random.random(shape + (num_parameters,))) for shape in shapes
        ]

        pubs[0][0].metadata = {"list": [1, 2, 3]}
        pubs[1][0].metadata = {"tuple": (1, 2, 3)}  # the tuple will be converted to a list

        options = SamplerOptions()
        options.twirling.enable_gates = twirling
        options.default_shots = 1000

        sampler = Sampler(self.backend, options)
        job = sampler.run(pubs)

        results = job.result()

        self.assertIsInstance(results, PrimitiveResult)
        self.assertIsInstance(results.metadata, dict)
        self.assertEqual(len(results), 2)

        for result, shape in zip(results, shapes):
            self.assertEqual(result.data.meas.shape, shape)

        self.assertEqual(results[0].metadata["circuit_metadata"], {"list": [1, 2, 3]})
        self.assertEqual(results[1].metadata["circuit_metadata"], {"tuple": [1, 2, 3]})
