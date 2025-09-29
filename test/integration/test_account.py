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
from ibm_platform_services import (
    ResourceControllerV2,
    GlobalSearchV2,
)  # pylint: disable=import-error

from qiskit_ibm_runtime import QiskitRuntimeService, IBMInputValueError
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime.utils.utils import (
    get_resource_controller_api_url,
    get_iam_api_url,
    get_global_search_api_url,
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


def _get_instance_tags(
    dependencies: IntegrationTestDependencies,
) -> Dict[str, str]:
    """Retrieves the service instance tags for a given crn."""
    authenticator = IAMAuthenticator(dependencies.token, url=get_iam_api_url(dependencies.url))
    client = GlobalSearchV2(authenticator=authenticator)
    client.set_service_url(get_global_search_api_url(dependencies.url))
    items = client.search(query="service_name:quantum-computing", fields=["tags"]).get_result()[
        "items"
    ]
    for item in items:
        if item.get("tags"):
            return item["tags"]
    return None


class TestQuantumPlatform(IBMIntegrationTestCase):
    """Integration tests for account management."""

    def test_initializing_service_no_instance(self):
        """Test initializing without an instance."""

        # no default instance and no filters
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            service = QiskitRuntimeService(
                token=self.dependencies.token,
                channel="ibm_quantum_platform",
                url=self.dependencies.url,
            )
            self.assertTrue(service)
            message = logs.output[1]
            self.assertIn("Free and trial", message)

        # no defualt instance and plans_preference
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            service = QiskitRuntimeService(
                token=self.dependencies.token,
                channel="ibm_quantum_platform",
                url=self.dependencies.url,
                plans_preference=["internal"],
            )
            self.assertTrue(service)
            message = logs.output[1]
            self.assertNotIn("Free and trial", message)
            self.assertIn("available account instances are", message)

        # no defualt instance and region
        region = "us-east"
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            service = QiskitRuntimeService(
                token=self.dependencies.token,
                channel="ibm_quantum_platform",
                url=self.dependencies.url,
                region=region,
            )
            self.assertTrue(service)
            message = logs.output[1]
            self.assertIn("Free and trial", message)
            self.assertIn(f"region: {region}", message)

    def test_backends_default_instance(self):
        """Test that default instance returns the correct backends."""
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

    def test_account_plans_preference(self):
        """Test one valid and one invalid plans_preference."""
        plans_preference = ["internal"]
        service = QiskitRuntimeService(
            token=self.dependencies.token,
            url=self.dependencies.url,
            channel="ibm_quantum_platform",
            plans_preference=plans_preference,
        )

        first_instance = service._backend_instance_groups[0]
        self.assertEqual(plans_preference[0], first_instance.get("plan"))

        plans_preference_one_invalid = ["internal", "invalid_plan"]
        service = QiskitRuntimeService(
            token=self.dependencies.token,
            url=self.dependencies.url,
            channel="ibm_quantum_platform",
            plans_preference=plans_preference_one_invalid,
        )

        first_instance = service._backend_instance_groups[0]
        self.assertEqual(plans_preference_one_invalid[0], first_instance.get("plan"))

        with self.assertRaises(IBMInputValueError):
            service = QiskitRuntimeService(
                token=self.dependencies.token,
                url=self.dependencies.url,
                channel="ibm_quantum_platform",
                plans_preference=["invalid_plan"],
            )

    def test_account_region_preference(self):
        """Test account preferences region and plans_preference."""
        region = "us-east"
        service = QiskitRuntimeService(
            token=self.dependencies.token,
            url=self.dependencies.url,
            channel="ibm_quantum_platform",
            region=region,
        )

        service.backends()
        first_instance = service._backend_instance_groups[0]
        self.assertIn(region, first_instance.get("crn"))

        with self.assertRaises(IBMInputValueError):
            service = QiskitRuntimeService(
                token=self.dependencies.token,
                url=self.dependencies.url,
                channel="ibm_quantum_platform",
                region="invalid_region",
            )

    def test_account_preferences_tags(self):
        """Test tags account preference."""
        tags = _get_instance_tags(self.dependencies)
        if tags:
            service = QiskitRuntimeService(
                token=self.dependencies.token,
                url=self.dependencies.url,
                channel="ibm_quantum_platform",
                tags=tags,
            )

            instances = service._backend_instance_groups
            if instances:
                for instance in instances:
                    self.assertEqual(instance["tags"], tags)

        invalid_tags = ["invalid_tags"]
        with self.assertRaises(IBMInputValueError):
            service = QiskitRuntimeService(
                token=self.dependencies.token,
                url=self.dependencies.url,
                channel="ibm_quantum_platform",
                tags=invalid_tags,
            )

    def test_instances(self):
        """Test instances method."""
        service = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )
        instances = service.instances()
        self.assertTrue(instances)
        self.assertTrue(instances[0]["crn"])
        self.assertTrue(instances[0]["name"])

    def test_active_instance(self):
        """Test active_instance method."""
        instance = self.dependencies.instance
        service = QiskitRuntimeService(
            token=self.dependencies.token,
            channel="ibm_quantum_platform",
            url=self.dependencies.url,
            instance=instance,
        )
        self.assertEqual(instance, service.active_instance())

    def test_jobs_before_backend(self):
        """Test retrieving jobs before backends call."""
        service = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )
        self.assertTrue(service._all_instances)
        jobs = service.jobs()
        self.assertTrue(jobs)
        job = jobs[0]
        self.assertTrue(job.status())

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

    def test_service_usage(self):
        """Test usage method."""
        service = QiskitRuntimeService(
            token=self.dependencies.token, channel="ibm_quantum_platform", url=self.dependencies.url
        )
        usage = service.usage()
        self.assertTrue(usage)
        self.assertIsInstance(usage["usage_remaining_seconds"], int)
        self.assertIsInstance(usage, dict)


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
