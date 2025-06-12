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

from typing import Dict
import requests
from ibm_cloud_sdk_core.authenticators import (  # pylint: disable=import-error
    IAMAuthenticator,
)
from ibm_platform_services import ResourceControllerV2  # pylint: disable=import-error

from qiskit_ibm_runtime import QiskitRuntimeService, IBMInputValueError
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime.utils.utils import (
    get_resource_controller_api_url,
    get_iam_api_url,
)
from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import IntegrationTestDependencies


def _get_service_instance_name_for_crn(
    dependencies: IntegrationTestDependencies,
) -> Dict[str, str]:
    """Retrieves the service instance name and account id for a given CRN.

    Note: production code computes the inverse mapping. This function is needed for integration test
        purposes only.
    """
    authenticator = IAMAuthenticator(dependencies.token, url=get_iam_api_url(dependencies.url))
    client = ResourceControllerV2(authenticator=authenticator)
    with requests.Session() as session:
        client.set_service_url(get_resource_controller_api_url(dependencies.url))
        client.set_http_client(session)
        return client.get_resource_instance(id=dependencies.instance).get_result()["name"]


class TestQuantumPlatform(IBMIntegrationTestCase):
    """Integration tests for account management."""

    def _skip_on_ibm_quantum(self):
        if self.dependencies.channel == "ibm_quantum":
            self.skipTest("Not supported on ibm_quantum")

    def test_initializing_service_no_instance(self):
        """Test initializing without an instance."""
        self._skip_on_ibm_quantum()
        service = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )
        self.assertTrue(service)
        self.assertTrue(service.backends())

    def test_backends_default_instance(self):
        """Test that default instance returns the correct backends."""
        self._skip_on_ibm_quantum()
        service_with_instance = QiskitRuntimeService(
            token=self.dependencies.token,
            url=self.dependencies.url,
            instance=self.dependencies.instance,
            channel="ibm_quantum_platform",
        )
        backends = service_with_instance.backends()
        backend = service_with_instance.backend(name=self.dependencies.qpu)

        service_no_instance = QiskitRuntimeService(
            token=self.dependencies.token, url=self.dependencies.url, channel="ibm_quantum_platform"
        )
        backends_with_instance = service_no_instance.backends(instance=self.dependencies.instance)
        backend_with_instance = service_no_instance.backend(
            name=self.dependencies.qpu, instance=self.dependencies.instance
        )
        self.assertEqual(
            [backend.name for backend in backends],
            [backend.name for backend in backends_with_instance],
        )
        self.assertEqual(backend.name, backend_with_instance.name)

    def test_passing_name_as_instance(self):
        """Test passing in a name as the instance."""
        self._skip_on_ibm_quantum()
        with self.assertRaises(IBMInputValueError):
            QiskitRuntimeService(
                token=self.dependencies.token,
                instance="test_name",
                channel="ibm_quantum_platform",
                url=self.dependencies.url,
            )

        service_instance_name = _get_service_instance_name_for_crn(self.dependencies)
        service = QiskitRuntimeService(
            token=self.dependencies.token,
            instance=service_instance_name,
            channel="ibm_quantum_platform",
            url=self.dependencies.url,
        )
        self.assertEqual(service._account.instance, self.dependencies.instance)
        service_no_instance = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )

        backends = service.backends()
        backends_instance_param = service_no_instance.backends(instance=service_instance_name)
        self.assertEqual(
            [backend.name for backend in backends],
            [backend.name for backend in backends_instance_param],
        )

    def test_account_preferences(self):
        """Test account preferences region and plans_preference."""
        region = "us-east"
        plans_preference = ["internal"]
        service = QiskitRuntimeService(
            token=self.dependencies.token,
            url=self.dependencies.url,
            channel="ibm_quantum_platform",
            region=region,
            plans_preference=plans_preference,
        )

        service.backends()
        first_instance = service._backend_instance_groups[0]
        self.assertIn(region, first_instance.get("crn"))
        self.assertEqual(plans_preference[0], first_instance.get("plan"))

    def test_instances(self):
        """Test instances method."""
        service = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )
        instances = service.instances()
        self.assertTrue(instances)
        self.assertTrue(instances[0]["crn"])
        self.assertTrue(instances[0]["name"])

    def test_jobs_before_backend(self):
        """Test retrieving jobs before backends call."""
        service = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )
        self.assertTrue(service._all_instances)
        jobs = service.jobs()
        self.assertTrue(jobs)
        job = jobs[0]
        self.assertTrue(job.result())

    def test_jobs_different_instances(self):
        """Test retrieving jobs from different instances."""
        service = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )
        instances = service.instances()
        for instance in instances:
            instance_service = QiskitRuntimeService(
                token=self.dependencies.token,
                instance=instance["crn"],
                channel="ibm_quantum_platform",
                url=self.dependencies.url,
            )
            jobs = instance_service.jobs()
            if jobs:
                instance_job = jobs[0].job_id()
                self.assertTrue(service.job(instance_job))


class TestIntegrationAccount(IBMIntegrationTestCase):
    """Integration tests for account management."""

    def test_local_channel(self):
        """Test local channel mode"""
        local_service = QiskitRuntimeService(
            channel="local",
        )
        local_service1 = QiskitRuntimeService(
            channel="local",
            url=self.dependencies.url,
            token=self.dependencies.token,
            instance=self.dependencies.instance,
        )
        self.assertIsInstance(local_service, QiskitRuntimeLocalService)
        self.assertIsInstance(local_service1, QiskitRuntimeLocalService)

    def test_resolve_crn_for_valid_service_instance_name(self):
        """Verify if CRN is transparently resolved based for an existing service instance name."""

        service_instance_name = _get_service_instance_name_for_crn(self.dependencies)
        with self.subTest(instance=service_instance_name):
            service = QiskitRuntimeService(
                channel="ibm_cloud",
                url=self.dependencies.url,
                token=self.dependencies.token,
                instance=self.dependencies.instance,
            )
            self.assertEqual(self.dependencies.instance, service._account.instance)
            self.assertEqual(self.dependencies.instance, service.active_account().get("instance"))

    def test_resolve_crn_for_invalid_service_instance_name(self):
        """Verify if CRN resolution fails for non-existing service instance name."""

        service_instance_name = "-non-existing-service-name-"
        with (
            self.subTest(instance="-non-existing-service-name-"),
            self.assertRaises(IBMInputValueError),
        ):
            QiskitRuntimeService(
                channel="ibm_cloud",
                url=self.dependencies.url,
                token=self.dependencies.token,
                instance=service_instance_name,
            )
