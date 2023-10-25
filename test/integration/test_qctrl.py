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

import time
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.providers.jobstatus import JobStatus

from qiskit_ibm_runtime import Sampler, Session, Options

from ..ibm_test_case import IBMIntegrationJobTestCase
from ..decorators import run_integration_test, cloud_only
from ..utils import cancel_job_safe


class TestQCTRL(IBMIntegrationJobTestCase):
    """Integration tests for QCTRL integration."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = ReferenceCircuits.bell()
        self.backend = "ibmq_qasm_simulator"
        # does q-ctrl work with simulator?
        # self.dependencies.service.least_busy(simulator=False)

    @run_integration_test
    @cloud_only
    def test_qctrl(self, service):
        """Test simple bell circuit."""
        service._channel_strategy = "q-ctrl"
        with Session(service, self.backend) as session:
            options = Options(resilience_level=1)
            sampler = Sampler(session=session, options=options)

            result = sampler.run(circuits=self.bell).result()
            self.assertTrue(result)

    @run_integration_test
    @cloud_only
    def test_cancel_qctrl_job(self, service):
        """Test canceling qctrl job."""
        service._channel_strategy = "q-ctrl"

        with Session(service, self.backend) as session:
            options = Options(resilience_level=1)
            sampler = Sampler(session=session, options=options)

            job = sampler.run([self.bell] * 10)

        rjob = service.job(job.job_id())
        if not cancel_job_safe(rjob, self.log):
            return
        time.sleep(5)
        self.assertEqual(rjob.status(), JobStatus.CANCELLED)
