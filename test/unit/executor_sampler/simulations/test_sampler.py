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

"""SamplerV2 tests centered around qiskit-aer simulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from ddt import data, ddt, unpack
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.quantum_info import Statevector, hellinger_fidelity
from qiskit_aer import AerSimulator

from qiskit_ibm_runtime.decoders.executor_sampler.post_processor_v0_1 import (
    sampler_v2_post_processor_v0_1,
)
from qiskit_ibm_runtime.executor_sampler import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.sim_executor import SimExecutor

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases

if TYPE_CHECKING:
    from qiskit.result import SamplerPubResult


@ddt
class TestSampler(IBMTestCase):
    """SamplerV2 tests centered around qiskit-aer simulations.

    All the tests in this class perform noiseless simulations.
    """

    def setUp(self):
        """Test level setup."""
        super().setUp()

        self.backend = FakeManilaV2()

        # The tolerance used when verifying simulated counts with exact probabilities via
        # Hellinger distance.
        self.tolerance = 0.01

    def verify_pub_result(self, pub: SamplerPub, pub_result: SamplerPubResult) -> None:
        """A helper to verify the correctness of PUB results.

        It computes the probabilities of each outcome exactly using Qiskit's StateVector class.
        Then, it compares them to the given ``counts`` via Hellinger distance.
        """
        # Avoid modifying the given circuit
        circuit_cp = pub.circuit.copy()
        circuit_cp.remove_final_measurements()

        parameter_values = pub.parameter_values
        if len(parameter_values.shape) == 0:
            parameter_values = parameter_values.reshape((1,) + parameter_values.shape)

        for index in np.ndindex(parameter_values.shape):
            assigned_parameters = parameter_values[index].as_array(pub.circuit.parameters)
            bound_circuit = circuit_cp.assign_parameters(assigned_parameters)
            probabilities = Statevector(bound_circuit).probabilities_dict()

            counts = pub_result.data.meas[index].get_counts()

            self.assertAlmostEqual(
                fidelity := hellinger_fidelity(counts, probabilities),
                1.0,
                msg=f"Fidelity: {fidelity}",
                delta=self.tolerance,
            )

    @data([True, False], [False, True], [True, True], [False, False])
    @unpack
    def test_twirling_configurations(self, enable_gates, enable_measure):
        """Test sampler with different configurations of twirling."""
        circuit = make_mirror_circuit_with_phases(self.backend)
        parameters = np.random.random((2, 3) + (circuit.num_parameters,))

        pubs = [SamplerPub.coerce([circuit, parameters])]

        # TODO: This is a temporary patch that can be removed when sampler supports
        # local mode via executor's own local mode.
        sampler = SamplerV2(self.backend)
        sampler._executor = SimExecutor(AerSimulator())

        sampler.options.twirling.enable_gates = enable_gates
        sampler.options.twirling.enable_measure = enable_measure
        sampler.options.twirling.num_randomizations = (num_randomizations := 32)
        sampler.options.twirling.shots_per_randomization = (shots_per_randomization := 100)

        job = sampler.run(pubs, shots=(shots := 4_000))

        # TODO: This is a temporary patch that can be removed when sampler supports
        # local mode via executor's own local mode.
        executor_result = job.result()
        result = sampler_v2_post_processor_v0_1(executor_result)

        array = result[0].data.meas
        self.assertEqual(
            array.num_shots,
            num_randomizations * shots_per_randomization
            if enable_measure or enable_gates
            else shots,
        )
        self.assertEqual(array.shape, pubs[0].shape)

        for pub, pub_result in zip(pubs, result):
            self.verify_pub_result(pub, pub_result)
