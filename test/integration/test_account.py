# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for account management."""

import requests
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_platform_services import ResourceControllerV2

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts import CloudResourceNameResolutionError
from qiskit_ibm_runtime.utils.utils import (
    get_resource_controller_api_url,
    get_iam_api_url,
)
from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import IntegrationTestDependencies


def _get_service_instance_name_for_crn(
    dependencies: IntegrationTestDependencies,
) -> str:
    """Retrieves the service instance name for a given CRN.

    Note: production code computes the inverse mapping. This function is needed for integration test
        purposes only.
    """
    authenticator = IAMAuthenticator(
        dependencies.token, url=get_iam_api_url(dependencies.url)
    )
    client = ResourceControllerV2(authenticator=authenticator)
    with requests.Session() as session:
        client.set_service_url(get_resource_controller_api_url(dependencies.url))
        client.set_http_client(session)
        return client.get_resource_instance(id=dependencies.instance).get_result()[
            "name"
        ]


class TestIntegrationAccount(IBMIntegrationTestCase):
    """Integration tests for account management."""

    def _skip_on_ibm_quantum(self):
        if self.dependencies.channel == "ibm_quantum":
            self.skipTest("Not supported on ibm_quantum")

    def test_resolve_crn_for_valid_service_instance_name(self):
        """Verify if CRN is transparently resolved based for an existing service instance name."""
        self._skip_on_ibm_quantum()

        service_instance_name = _get_service_instance_name_for_crn(self.dependencies)
        with self.subTest(instance=service_instance_name):
            service = QiskitRuntimeService(
                channel="ibm_cloud",
                url=self.dependencies.url,
                token=self.dependencies.token,
                instance=service_instance_name,
            )
            self.assertEqual(self.dependencies.instance, service._account.instance)
            self.assertEqual(
                self.dependencies.instance, service.active_account().get("instance")
            )

    def test_resolve_crn_for_invalid_service_instance_name(self):
        """Verify if CRN resolution fails for non-existing service instance name."""
        self._skip_on_ibm_quantum()

        service_instance_name = "-non-existing-service-name-"
        with self.subTest(instance="-non-existing-service-name-"), self.assertRaises(
            CloudResourceNameResolutionError
        ):
            QiskitRuntimeService(
                channel="ibm_cloud",
                url=self.dependencies.url,
                token=self.dependencies.token,
                instance=service_instance_name,
            )
