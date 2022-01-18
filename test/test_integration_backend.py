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

"""Tests for backend functions using real runtime service."""

from unittest import SkipTest

from .ibm_test_case import IBMIntegrationTestCase
from .utils.decorators import (
    run_cloud_legacy_real,
    requires_cloud_legacy_devices,
)


class TestIntegrationBackend(IBMIntegrationTestCase):
    """Integration tests for backend functions."""

    @run_cloud_legacy_real
    def test_backends(self, service):
        """Test getting all backends."""
        backends = service.backends()
        self.assertTrue(backends)
        backend_names = [back.name() for back in backends]
        self.assertEqual(
            len(backend_names),
            len(set(backend_names)),
            f"backend_names={backend_names}",
        )

    @run_cloud_legacy_real
    def test_get_backend(self, service):
        """Test getting a backend."""
        backends = service.backends()
        backend = service.backend(backends[0].name())
        self.assertTrue(backend)


class TestIBMBackend(IBMIntegrationTestCase):
    """Test ibm_backend module."""

    @classmethod
    @requires_cloud_legacy_devices
    def setUpClass(cls, devices):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        # pylint: disable=no-value-for-parameter
        super().setUpClass()
        cls.devices = devices

    def test_backend_status(self):
        """Check the status of a real chip."""
        for backend in self.devices:
            with self.subTest(backend=backend.name()):
                self.assertTrue(backend.status().operational)

    def test_backend_properties(self):
        """Check the properties of calibration of a real chip."""
        for backend in self.devices:
            with self.subTest(backend=backend.name()):
                if backend.configuration().simulator:
                    raise SkipTest("Skip since simulator does not have properties.")
                self.assertIsNotNone(backend.properties())

    def test_backend_pulse_defaults(self):
        """Check the backend pulse defaults of each backend."""
        for backend in self.devices:
            with self.subTest(backend=backend.name()):
                if backend.configuration().simulator:
                    raise SkipTest("Skip since simulator does not have defaults.")
                self.assertIsNotNone(backend.defaults())

    def test_backend_configuration(self):
        """Check the backend configuration of each backend."""
        for backend in self.devices:
            with self.subTest(backend=backend.name()):
                self.assertIsNotNone(backend.configuration())

    def test_backend_run(self):
        """Check one cannot do backend.run"""
        for backend in self.devices:
            with self.subTest(backend=backend.name()):
                with self.assertRaises(RuntimeError):
                    backend.run()
