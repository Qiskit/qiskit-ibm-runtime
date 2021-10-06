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
from unittest import SkipTest
from unittest.mock import patch

from qiskit import QuantumCircuit
from qiskit.providers.models import QasmBackendConfiguration
from qiskit.test.reference_circuits import ReferenceCircuits

from ..ibm_test_case import IBMTestCase
from ..decorators import requires_device, requires_provider
from ..utils import get_pulse_schedule, cancel_job


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
        provider = self.backend.provider()
        for backend in provider.backends():
            with self.subTest(backend_name=backend.name()):
                defaults = backend.defaults()
                if backend.configuration().open_pulse:
                    self.assertIsNotNone(defaults)

    def test_backend_reservations(self):
        """Test backend reservations."""
        provider = self.backend.provider()
        backend = reservations = None
        for backend in provider.backends(simulator=False, operational=True):
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
            (before_start, after_end, True, 'before start, after end'),
            (before_start, before_end, True, 'before start, before end'),
            (after_start, before_end, True, 'after start, before end'),
            (before_start, None, True, 'before start, None'),
            (None, after_end, True, 'None, after end'),
            (before_start, before_start, False, 'before start, before start'),
            (after_end, after_end, False, 'after end, after end')
        ]

        for start_dt, end_dt, should_find, name in sub_tests:
            with self.subTest(name=name):
                f_reservs = backend.reservations(start_datetime=start_dt, end_datetime=end_dt)
                found = False
                for f_reserv in f_reservs:
                    if f_reserv == reserv:
                        found = True
                        break
                self.assertEqual(
                    found, should_find,
                    "Reservation {} found={}, used start datetime {}, end datetime {}".format(
                        reserv, found, start_dt, end_dt))

    def test_backend_options(self):
        """Test backend options."""
        provider = self.backend.provider()
        backends = provider.backends(open_pulse=True, operational=True)
        if not backends:
            raise SkipTest('Skipping pulse test since no pulse backend found.')

        backend = backends[0]
        backend.options.shots = 2048
        backend.set_options(qubit_lo_freq=[4.9e9, 5.0e9],
                            meas_lo_freq=[6.5e9, 6.6e9],
                            meas_level=2)
        job = backend.run(get_pulse_schedule(backend), meas_level=1, foo='foo')
        backend_options = provider.backend.job(job.job_id()).backend_options()
        self.assertEqual(backend_options['shots'], 2048)
        # Qobj config freq is in GHz.
        self.assertAlmostEqual(backend_options['qubit_lo_freq'], [4.9e9, 5.0e9])
        self.assertEqual(backend_options['meas_lo_freq'], [6.5e9, 6.6e9])
        self.assertEqual(backend_options['meas_level'], 1)
        self.assertEqual(backend_options['foo'], 'foo')
        cancel_job(job)

    def test_sim_backend_options(self):
        """Test simulator backend options."""
        provider = self.backend.provider()
        backend = provider.get_backend('ibmq_qasm_simulator')
        backend.options.shots = 2048
        backend.set_options(memory=True)
        job = backend.run(ReferenceCircuits.bell(), shots=1024, foo='foo')
        backend_options = provider.backend.job(job.job_id()).backend_options()
        self.assertEqual(backend_options['shots'], 1024)
        self.assertTrue(backend_options['memory'])
        self.assertEqual(backend_options['foo'], 'foo')

    def test_deprecate_id_instruction(self):
        """Test replacement of 'id' Instructions with 'Delay' instructions."""

        circuit_with_id = QuantumCircuit(2)
        circuit_with_id.id(0)
        circuit_with_id.id(0)
        circuit_with_id.id(1)

        config = QasmBackendConfiguration(
            basis_gates=['id'],
            supported_instructions=['delay'],
            dt=0.25,
            backend_name='test',
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

        with patch.object(self.backend, 'configuration', return_value=config):
            with self.assertWarnsRegex(DeprecationWarning, r"'id' instruction"):
                self.backend._deprecate_id_instruction(circuit_with_id)

            self.assertEqual(circuit_with_id.count_ops(), {'delay': 3})


class TestIBMBackendService(IBMTestCase):
    """Test ibm_backend_service module."""

    @classmethod
    @requires_provider
    def setUpClass(cls, provider):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.provider = provider
        cls.last_week = datetime.now() - timedelta(days=7)

    def test_my_reservations(self):
        """Test my_reservations method"""
        reservations = self.provider.backend.my_reservations()
        for reserv in reservations:
            for attr in reserv.__dict__:
                self.assertIsNotNone(
                    getattr(reserv, attr),
                    "Reservation {} is missing attribute {}".format(reserv, attr))
