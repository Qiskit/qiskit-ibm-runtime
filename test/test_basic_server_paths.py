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

"""Tests that hit all the basic server endpoints using both a public and premium h/g/p."""

from .ibm_test_case import IBMTestCase
from .utils.decorators import requires_multiple_hgps


class TestBasicServerPaths(IBMTestCase):
    """Test the basic server endpoints using both a public and premium provider."""

    @classmethod
    @requires_multiple_hgps
    def setUpClass(cls, service, open_hgp, premium_hgp):
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.service = service  # Dict[str, IBMRuntimeService]
        cls.hgps = [open_hgp, premium_hgp]

    def test_device_properties_and_defaults(self):
        """Test device properties and defaults."""
        for hgp in self.hgps:
            with self.subTest(hgp=hgp):
                pulse_backends = self.service.backends(
                    simulator=False, operational=True, instance=hgp
                )
                if not pulse_backends:
                    raise self.skipTest(
                        "Skipping pulse test since no pulse backend "
                        'found for "{}"'.format(hgp)
                    )

                self.assertIsNotNone(pulse_backends[0].properties())
                self.assertIsNotNone(pulse_backends[0].defaults())

    def test_device_status(self):
        """Test device status."""
        for hgp in self.hgps:
            with self.subTest(hgp=hgp):
                backend = self.service.backends(
                    simulator=False, operational=True, instance=hgp
                )[0]
                self.assertTrue(backend.status())
