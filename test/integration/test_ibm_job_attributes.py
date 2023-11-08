# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test IBMJob attributes."""

import uuid
from datetime import datetime, timedelta

from dateutil import tz
from qiskit.compiler import transpile
from qiskit import QuantumCircuit
from qiskit.test.reference_circuits import ReferenceCircuits

from qiskit_ibm_provider.exceptions import (
    IBMBackendValueError,
)

from qiskit_ibm_runtime import IBMBackend, RuntimeJob
from ..decorators import (
    IntegrationTestDependencies,
    integration_test_setup,
)
from ..ibm_test_case import IBMTestCase


class TestIBMJobAttributes(IBMTestCase):
    """Test IBMJob instance attributes."""

    sim_backend: IBMBackend
    bell: QuantumCircuit
    sim_job: RuntimeJob
    last_week: datetime

    @classmethod
    @integration_test_setup()
    def setUpClass(cls, dependencies: IntegrationTestDependencies) -> None:
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.dependencies = dependencies
        cls.service = dependencies.service
        cls.sim_backend = dependencies.service.backend("ibmq_qasm_simulator")
        cls.bell = transpile(ReferenceCircuits.bell(), cls.sim_backend)
        cls.sim_job = cls.sim_backend.run(cls.bell)
        cls.last_week = datetime.now() - timedelta(days=7)

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self._qc = ReferenceCircuits.bell()

    def test_job_id(self):
        """Test getting a job ID."""
        self.assertTrue(self.sim_job.job_id() is not None)

    def test_get_backend_name(self):
        """Test getting a backend name."""
        self.assertTrue(self.sim_job.backend().name == self.sim_backend.name)

    def test_job_creation_date(self):
        """Test retrieving creation date, while ensuring it is in local time."""
        # datetime, before running the job, in local time.
        start_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) - timedelta(seconds=1)
        job = self.sim_backend.run(self.bell)
        job.result()
        # datetime, after the job is done running, in local time.
        end_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) + timedelta(seconds=1)

        self.assertTrue(
            (start_datetime <= job.creation_date <= end_datetime),
            "job creation date {} is not "
            "between the start date time {} and end date time {}".format(
                job.creation_date, start_datetime, end_datetime
            ),
        )

    def test_esp_readout_not_enabled(self):
        """Test that an error is thrown is ESP readout is used and the backend does not support it."""
        # sim backend does not have ``measure_esp_enabled`` flag: defaults to ``False``
        with self.assertRaises(IBMBackendValueError) as context_manager:
            self.sim_backend.run(self.bell, use_measure_esp=True)
        self.assertIn(
            "ESP readout not supported on this device. Please make sure the flag "
            "'use_measure_esp' is unset or set to 'False'.",
            context_manager.exception.message,
        )

    def test_esp_readout_enabled(self):
        """Test that ESP readout can be used when the backend supports it."""
        try:
            setattr(self.sim_backend._configuration, "measure_esp_enabled", True)
            job = self.sim_backend.run(self.bell, use_measure_esp=True)
            self.assertEqual(job.inputs["use_measure_esp"], True)
        finally:
            delattr(self.sim_backend._configuration, "measure_esp_enabled")

    def test_esp_readout_default_value(self):
        """Test that ESP readout is set to backend support value if not specified."""
        try:
            # ESP readout not enabled on backend
            setattr(self.sim_backend._configuration, "measure_esp_enabled", False)
            job = self.sim_backend.run(self.bell)
            self.assertIsNone(getattr(job.inputs, "use_measure_esp", None))
            # ESP readout enabled on backend
            setattr(self.sim_backend._configuration, "measure_esp_enabled", True)
            job = self.sim_backend.run(self.bell, use_measure_esp=True)
            self.assertEqual(job.inputs["use_measure_esp"], True)
        finally:
            delattr(self.sim_backend._configuration, "measure_esp_enabled")

    def test_job_tags(self):
        """Test using job tags."""
        # Use a unique tag.
        job_tags = [
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
        ]
        job = self.sim_backend.run(self.bell, job_tags=job_tags)

        no_rjobs_tags = [job_tags[0:1] + ["phantom_tags"], ["phantom_tag"]]
        for tags in no_rjobs_tags:
            rjobs = self.service.jobs(job_tags=tags, created_after=self.last_week)
            self.assertEqual(len(rjobs), 0, "Expected job {}, got {}".format(job.job_id(), rjobs))

        has_rjobs_tags = [job_tags, job_tags[1:3]]
        for tags in has_rjobs_tags:
            with self.subTest(tags=tags):
                rjobs = self.service.jobs(
                    job_tags=tags,
                    created_after=self.last_week,
                )
                self.assertEqual(
                    len(rjobs), 1, "Expected job {}, got {}".format(job.job_id(), rjobs)
                )
                self.assertEqual(rjobs[0].job_id(), job.job_id())
                # TODO check why this sometimes fails
                # self.assertEqual(set(rjobs[0].tags()), set(job_tags))

    def test_invalid_job_tags(self):
        """Test using job tags with an and operator."""
        self.assertRaises(ValueError, self.sim_backend.run, self.bell, job_tags={"foo"})
        self.assertRaises(
            ValueError,
            self.service.jobs,
            job_tags=[1, 2, 3],
        )

    def test_cost_estimation(self):
        """Test cost estimation is returned correctly."""
        self.assertTrue(self.sim_job.usage_estimation)
        self.assertIn("quantum_seconds", self.sim_job.usage_estimation)
