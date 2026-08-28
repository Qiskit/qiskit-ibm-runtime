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

from qiskit_ibm_runtime.executor_sampler import SamplerV2

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

        self.backend = AerSimulator()

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

        # Convert to at least 1D array, so that we can loop through its elements.
        parameter_values = pub.parameter_values.as_array(pub.circuit.parameters)
        parameter_values = np.atleast_1d(parameter_values)

        array = pub_result.data.meas
        self.assertEqual(array.shape, pub.shape)

        for index in np.ndindex(parameter_values.shape[:-1]):
            assigned_parameters = parameter_values[index]
            bound_circuit = circuit_cp.assign_parameters(assigned_parameters)
            probabilities = Statevector(bound_circuit).probabilities_dict()

            self.assertAlmostEqual(
                fidelity := hellinger_fidelity(array[index].get_counts(), probabilities),
                1.0,
                msg=f"Fidelity: {fidelity}",
                delta=self.tolerance,
            )

    @data([True, False], [False, True], [True, True], [False, False])
    @unpack
    def test_twirling_configurations(self, enable_gates, enable_measure):
        """Test sampler with different configurations of twirling.

        Checks that:
        * The pub results match with the correct results, regardless of the twirling
          strategy.
        * The number of shots equals ``num_randomizations * shots_per_randomization`` when
          either gate or measurement twirling is enabled, and the requested ``shots``
          otherwise.
        """
        circuit = make_mirror_circuit_with_phases(self.backend)
        parameters = np.random.random((2, 3) + (circuit.num_parameters,))

        pubs = [SamplerPub.coerce([circuit, parameters])]

        sampler = SamplerV2(self.backend)
        sampler.options.experimental = {"local_mode": True}

        sampler.options.twirling.enable_gates = enable_gates
        sampler.options.twirling.enable_measure = enable_measure
        sampler.options.twirling.num_randomizations = (num_randomizations := 32)
        sampler.options.twirling.shots_per_randomization = (shots_per_randomization := 100)

        job = sampler.run(pubs, shots=(shots := 4_000))
        result = job.result()

        array = result[0].data.meas
        self.assertEqual(
            array.num_shots,
            num_randomizations * shots_per_randomization
            if enable_measure or enable_gates
            else shots,
        )

        for pub, pub_result in zip(pubs, result):
            self.verify_pub_result(pub, pub_result)
