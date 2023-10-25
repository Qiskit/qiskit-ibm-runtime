# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for job functions using real runtime service."""


from qiskit.test.reference_circuits import ReferenceCircuits

from qiskit_ibm_runtime import Sampler, Session

from ..ibm_test_case import IBMIntegrationJobTestCase
from ..decorators import run_integration_test


class TestQCTRL(IBMIntegrationJobTestCase):
    """Integration tests for QCTRL integration."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = ReferenceCircuits.bell()
        self.backend = "ibmq_qasm_simulator"

    @run_integration_test
    def test_qctrl(self, service):
        """Test qctrl."""
        service._channel_strategy = "q-ctrl"
        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)

            result = sampler.run(circuits=self.bell).result()
            self.assertTrue(result)
