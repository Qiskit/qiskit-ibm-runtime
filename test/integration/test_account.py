# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for account management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
import requests
from ibm_cloud_sdk_core import ApiException
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_platform_services import GlobalSearchV2, ResourceControllerV2

from qiskit_ibm_runtime import IBMInputValueError, QiskitRuntimeService
from qiskit_ibm_runtime.accounts.utils import (
    get_global_search_api_url,
    get_iam_api_url,
    get_resource_controller_api_url,
)
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService

if TYPE_CHECKING:
    from .dependencies import Dependencies


def _get_service_instance_name_for_crn(
    dependencies: Dependencies,
) -> str:
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
    dependencies: Dependencies,
) -> list[str] | None:
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


class TestQuantumPlatform:
    """Integration tests for account management."""

    def test_initializing_service_no_instance(
        self, caplog: pytest.LogCaptureFixture, dependencies: Dependencies
    ) -> None:
        """Test initializing without an instance."""
        # no default instance and no filters
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            QiskitRuntimeService(
                token=dependencies.token,
                channel="ibm_quantum_platform",
                url=dependencies.url,
            )
            assert "Free and trial" in caplog.text

        # no default instance and plans_preference
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            QiskitRuntimeService(
                token=dependencies.token,
                channel="ibm_quantum_platform",
                url=dependencies.url,
                plans_preference=["internal"],
            )
            assert "Free and trial" not in caplog.text
            assert "available account instances are" in caplog.text

        # no default instance and region
        region = "us-east"
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            QiskitRuntimeService(
                token=dependencies.token,
                channel="ibm_quantum_platform",
                url=dependencies.url,
                region=region,
            )
            assert "Free and trial" in caplog.text
            assert f"region: {region}" in caplog.text

    def test_backends_default_instance(self, dependencies: Dependencies) -> None:
        """Test that default instance returns the correct backends."""
        service_with_instance = QiskitRuntimeService(
            token=dependencies.token,
            url=dependencies.url,
            instance=dependencies.instance,
            channel="ibm_quantum_platform",
        )
        backends = service_with_instance.backends()
        backend = service_with_instance.backend(name=dependencies.qpu)

        service_no_instance = QiskitRuntimeService(
            token=dependencies.token, url=dependencies.url, channel="ibm_quantum_platform"
        )
        backends_with_instance = service_no_instance.backends(instance=dependencies.instance)
        backend_with_instance = service_no_instance.backend(
            name=dependencies.qpu, instance=dependencies.instance
        )
        assert [backend.name for backend in backends] == [
            backend.name for backend in backends_with_instance
        ]
        assert backend.name == backend_with_instance.name

    def test_passing_name_as_instance(self, dependencies: Dependencies) -> None:
        """Test passing in a name as the instance."""
        with pytest.raises(IBMInputValueError):
            QiskitRuntimeService(
                token=dependencies.token,
                instance="test_name",
                channel="ibm_quantum_platform",
                url=dependencies.url,
            )

        service_instance_name = _get_service_instance_name_for_crn(dependencies)
        service = QiskitRuntimeService(
            token=dependencies.token,
            instance=service_instance_name,
            channel="ibm_quantum_platform",
            url=dependencies.url,
        )
        assert service._account.instance == dependencies.instance
        service_no_instance = QiskitRuntimeService(
            token=dependencies.token, channel="ibm_quantum_platform", url=dependencies.url
        )

        backends = service.backends()
        backends_instance_param = service_no_instance.backends(instance=service_instance_name)
        assert [backend.name for backend in backends] == [
            backend.name for backend in backends_instance_param
        ]

    def test_account_plans_preference(self, dependencies: Dependencies) -> None:
        """Test one valid and one invalid plans_preference."""
        plans_preference = ["internal"]
        service = QiskitRuntimeService(
            token=dependencies.token,
            url=dependencies.url,
            channel="ibm_quantum_platform",
            plans_preference=plans_preference,
        )

        first_instance = service._backend_instance_groups[0]
        assert plans_preference[0] == first_instance.get("plan")

        plans_preference_one_invalid = ["internal", "invalid_plan"]
        service = QiskitRuntimeService(
            token=dependencies.token,
            url=dependencies.url,
            channel="ibm_quantum_platform",
            plans_preference=plans_preference_one_invalid,
        )

        first_instance = service._backend_instance_groups[0]
        assert plans_preference_one_invalid[0] == first_instance.get("plan")

        with pytest.raises(IBMInputValueError):
            service = QiskitRuntimeService(
                token=dependencies.token,
                url=dependencies.url,
                channel="ibm_quantum_platform",
                plans_preference=["invalid_plan"],
            )

    def test_account_region_preference(self, dependencies: Dependencies) -> None:
        """Test account preferences region and plans_preference."""
        region = "us-east"
        service = QiskitRuntimeService(
            token=dependencies.token,
            url=dependencies.url,
            channel="ibm_quantum_platform",
            region=region,
        )

        service.backends()
        first_instance = service._backend_instance_groups[0]
        assert region in first_instance.get("crn")

        with pytest.raises(IBMInputValueError):
            service = QiskitRuntimeService(
                token=dependencies.token,
                url=dependencies.url,
                channel="ibm_quantum_platform",
                region="invalid_region",
            )

    def test_account_preferences_tags(self, dependencies: Dependencies) -> None:
        """Test tags account preference."""
        tags = _get_instance_tags(dependencies)
        if tags:
            service = QiskitRuntimeService(
                token=dependencies.token,
                url=dependencies.url,
                channel="ibm_quantum_platform",
                tags=tags,
            )

            instances = service._backend_instance_groups
            if instances:
                for instance in instances:
                    assert instance["tags"] == tags

        invalid_tags = ["invalid_tags"]
        with pytest.raises(IBMInputValueError):
            service = QiskitRuntimeService(
                token=dependencies.token,
                url=dependencies.url,
                channel="ibm_quantum_platform",
                tags=invalid_tags,
            )

    def test_instances(self, dependencies: Dependencies) -> None:
        """Test instances method."""
        service = QiskitRuntimeService(
            token=dependencies.token, channel="ibm_quantum_platform", url=dependencies.url
        )
        instances = service.instances()
        assert instances
        assert instances[0]["crn"]
        assert instances[0]["name"]

    def test_active_instance(self, dependencies: Dependencies) -> None:
        """Test active_instance method."""
        instance = dependencies.instance
        service = QiskitRuntimeService(
            token=dependencies.token,
            channel="ibm_quantum_platform",
            url=dependencies.url,
            instance=instance,
        )
        assert instance == service.active_instance()

    def test_jobs_before_backend(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs before backends call."""
        service = QiskitRuntimeService(
            token=dependencies.token, channel="ibm_quantum_platform", url=dependencies.url
        )
        assert service._all_instances
        jobs = service.jobs()
        assert jobs
        job = jobs[0]
        assert job.status()

    def test_jobs_different_instances(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs from different instances."""
        service = QiskitRuntimeService(
            token=dependencies.token, channel="ibm_quantum_platform", url=dependencies.url
        )
        instances = service.instances()
        for instance in instances:
            instance_service = QiskitRuntimeService(
                token=dependencies.token,
                instance=instance["crn"],
                channel="ibm_quantum_platform",
                url=dependencies.url,
            )
            jobs = instance_service.jobs()
            if jobs:
                instance_job = jobs[0].job_id()
                assert service.job(instance_job).job_id() == instance_job

    def test_service_usage(self, dependencies: Dependencies) -> None:
        """Test usage method."""
        service = QiskitRuntimeService(
            token=dependencies.token, channel="ibm_quantum_platform", url=dependencies.url
        )
        usage = service.usage()
        assert usage
        assert isinstance(usage["usage_remaining_seconds"], int)
        assert isinstance(usage, dict)

    def test_instances_archived(
        self, dependencies: Dependencies, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that archived instances are available to the user."""

        def mock_get_catalog_entry(*args, **kwargs):
            raise ApiException(403)

        monkeypatch.setattr(
            "ibm_platform_services.GlobalCatalogV1.get_catalog_entry",
            mock_get_catalog_entry,
        )
        service = QiskitRuntimeService(
            token=dependencies.token,
            channel="ibm_quantum_platform",
            url=dependencies.url,
        )
        instances = service.instances()
        assert instances
        assert all(
            instance["plan"] == "unknown" and instance["pricing_type"] == "unknown"
            for instance in instances
        )


class TestIntegrationAccount:
    """Integration tests for account management."""

    def test_local_channel(self, dependencies: Dependencies) -> None:
        """Test local channel mode."""
        local_service: object = QiskitRuntimeService(
            channel="local",
        )
        local_service1: object = QiskitRuntimeService(
            channel="local",
            url=dependencies.url,
            token=dependencies.token,
            instance=dependencies.instance,
        )
        assert isinstance(local_service, QiskitRuntimeLocalService)
        assert isinstance(local_service1, QiskitRuntimeLocalService)

    def test_resolve_crn_for_valid_service_instance_name(self, dependencies: Dependencies) -> None:
        """Verify if CRN is transparently resolved based for an existing service instance name."""
        service = QiskitRuntimeService(
            channel="ibm_cloud",
            url=dependencies.url,
            token=dependencies.token,
            instance=dependencies.instance,
        )
        assert dependencies.instance == service._account.instance
        assert dependencies.instance == service.active_account().get("instance")

    def test_resolve_crn_for_invalid_service_instance_name(
        self, dependencies: Dependencies
    ) -> None:
        """Verify if CRN resolution fails for non-existing service instance name."""
        service_instance_name = "-non-existing-service-name-"
        with pytest.raises(IBMInputValueError):
            QiskitRuntimeService(
                channel="ibm_cloud",
                url=dependencies.url,
                token=dependencies.token,
                instance=service_instance_name,
            )
