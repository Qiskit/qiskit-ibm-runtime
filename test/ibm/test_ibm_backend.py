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

"""IBMBackend Test."""

from datetime import timedelta, datetime
from unittest.mock import patch

from qiskit import QuantumCircuit
from qiskit.providers.models import QasmBackendConfiguration

from ..ibm_test_case import IBMTestCase
from ..decorators import requires_device, requires_provider


class TestIBMBackend(IBMTestCase):
    """Test ibm_backend module."""

    @classmethod
    @requires_device
    def setUpClass(cls, backend):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.backend = backend

    def test_backend_status(self):
        """Check the status of a real chip."""
        self.assertTrue(self.backend.status().operational)

    def test_backend_properties(self):
        """Check the properties of calibration of a real chip."""
        self.assertIsNotNone(self.backend.properties())

    def test_backend_job_limit(self):
        """Check the backend job limits of a real backend."""
        job_limit = self.backend.job_limit()
        self.assertIsNotNone(job_limit)
        self.assertIsNotNone(job_limit.active_jobs)
        if job_limit.maximum_jobs:
            self.assertGreater(job_limit.maximum_jobs, 0)

    def test_backend_pulse_defaults(self):
        """Check the backend pulse defaults of each backend."""
        service = self.backend.provider()
        for backend in service.backends():
            with self.subTest(backend_name=backend.name()):
                defaults = backend.defaults()
                if backend.configuration().open_pulse:
                    self.assertIsNotNone(defaults)

    def test_backend_reservations(self):
        """Test backend reservations."""
        service = self.backend.provider()
        backend = reservations = None
        for backend in service.backends(
            simulator=False,
            operational=True,
            hub=self.backend.hub,
            group=self.backend.group,
            project=self.backend.project,
        ):
            reservations = backend.reservations()
            if reservations:
                break

        if not reservations:
            self.skipTest("Test case requires reservations.")

        reserv = reservations[0]
        self.assertGreater(reserv.duration, 0)
        self.assertTrue(reserv.mode)
        before_start = reserv.start_datetime - timedelta(seconds=30)
        after_start = reserv.start_datetime + timedelta(seconds=30)
        before_end = reserv.end_datetime - timedelta(seconds=30)
        after_end = reserv.end_datetime + timedelta(seconds=30)

        # Each tuple contains the start datetime, end datetime, whether a
        # reservation should be found, and the description.
        sub_tests = [
            (before_start, after_end, True, "before start, after end"),
            (before_start, before_end, True, "before start, before end"),
            (after_start, before_end, True, "after start, before end"),
            (before_start, None, True, "before start, None"),
            (None, after_end, True, "None, after end"),
            (before_start, before_start, False, "before start, before start"),
            (after_end, after_end, False, "after end, after end"),
        ]

        for start_dt, end_dt, should_find, name in sub_tests:
            with self.subTest(name=name):
                f_reservs = backend.reservations(
                    start_datetime=start_dt, end_datetime=end_dt
                )
                found = False
                for f_reserv in f_reservs:
                    if f_reserv == reserv:
                        found = True
                        break
                self.assertEqual(
                    found,
                    should_find,
                    "Reservation {} found={}, used start datetime {}, end datetime {}".format(
                        reserv, found, start_dt, end_dt
                    ),
                )

    def test_deprecate_id_instruction(self):
        """Test replacement of 'id' Instructions with 'Delay' instructions."""

        circuit_with_id = QuantumCircuit(2)
        circuit_with_id.id(0)
        circuit_with_id.id(0)
        circuit_with_id.id(1)

        config = QasmBackendConfiguration(
            basis_gates=["id"],
            supported_instructions=["delay"],
            dt=0.25,
            backend_name="test",
            backend_version=0.0,
            n_qubits=1,
            gates=[],
            local=False,
            simulator=False,
            conditional=False,
            open_pulse=False,
            memory=False,
            max_shots=1,
            coupling_map=None,
        )

        with patch.object(self.backend, "configuration", return_value=config):
            with self.assertWarnsRegex(DeprecationWarning, r"'id' instruction"):
                self.backend._deprecate_id_instruction(circuit_with_id)

            self.assertEqual(circuit_with_id.count_ops(), {"delay": 3})


class TestIBMBackendService(IBMTestCase):
    """Test ibm_backend_service module."""

    @classmethod
    @requires_provider
    def setUpClass(cls, service, hub, group, project):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.service = service
        cls.hub = hub
        cls.group = group
        cls.project = project
        cls.last_week = datetime.now() - timedelta(days=7)

    def test_my_reservations(self):
        """Test my_reservations method"""
        reservations = self.service.my_reservations()
        for reserv in reservations:
            for attr in reserv.__dict__:
                self.assertIsNotNone(
                    getattr(reserv, attr),
                    "Reservation {} is missing attribute {}".format(reserv, attr),
                )
