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

"""Tests that hit all the basic server endpoints using both a public and premium provider."""

from datetime import datetime, timedelta

from ..decorators import requires_providers
from ..ibm_test_case import IBMTestCase


class TestBasicServerPaths(IBMTestCase):
    """Test the basic server endpoints using both a public and premium provider."""

    @classmethod
    @requires_providers
    def setUpClass(cls, service, hgps):
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.service = service  # Dict[str, IBMRuntimeService]
        cls.hgps = hgps
        cls.last_week = datetime.now() - timedelta(days=7)

    def test_device_properties_and_defaults(self):
        """Test the properties and defaults for an open pulse device."""
        for desc, hgp in self.hgps.items():
            pulse_backends = self.service.backends(
                open_pulse=True, operational=True, **hgp
            )
            if not pulse_backends:
                raise self.skipTest(
                    "Skipping pulse test since no pulse backend "
                    'found for "{}"'.format(desc)
                )

            pulse_backend = pulse_backends[0]
            with self.subTest(desc=desc, backend=pulse_backend):
                self.assertIsNotNone(pulse_backend.properties())
                self.assertIsNotNone(pulse_backend.defaults())

    def test_device_status(self):
        """Test device status."""
        for desc, hgp in self.hgps.items():
            backend = self.service.backends(simulator=False, operational=True, **hgp)[0]
            with self.subTest(desc=desc, backend=backend):
                self.assertTrue(backend.status())
