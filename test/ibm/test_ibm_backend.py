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

    def test_backend_pulse_defaults(self):
        """Check the backend pulse defaults of each backend."""
        service = self.backend.provider()
        for backend in service.backends():
            with self.subTest(backend_name=backend.name()):
                defaults = backend.defaults()
                if backend.configuration().open_pulse:
                    self.assertIsNotNone(defaults)
