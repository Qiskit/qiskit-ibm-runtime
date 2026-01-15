# This code is part of Qiskit.
#
# (C) Copyright IBM 2020, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=missing-module-docstring

from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import production_only


class TestRefreshFakeBackends(IBMIntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        # pylint: disable=arguments-differ
        # pylint: disable=no-value-for-parameter
        super().setUpClass()

    @production_only
    def test_refresh_method(self):
        """Test refresh method"""
        # to verify the data files will be updated
        old_backend = FakeSherbrooke()
        # change some configuration
        old_backend.backend_version = "fake_version"

        service = QiskitRuntimeService(
            token=self.dependencies.token,
            channel=self.dependencies.channel,
            url=self.dependencies.url,
        )

        # This tests needs access to the real device, and it might not be available.
        try:
            service.backend("ibm_sherbrooke")
        except QiskitBackendNotFoundError:
            self.skipTest("Credentials do not have access to ibm_sherbrooke")

        with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
            old_backend.refresh(service)
        self.assertIn("The backend fake_sherbrooke has been updated", logs.output[1])

        # to verify the refresh can't be done
        wrong_backend = FakeSherbrooke()
        # set a non-existent backend name
        wrong_backend.backend_name = "wrong_fake_sherbrooke"
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            wrong_backend.refresh(service)
        self.assertIn("The refreshing of wrong_fake_sherbrooke has failed", logs.output[0])
