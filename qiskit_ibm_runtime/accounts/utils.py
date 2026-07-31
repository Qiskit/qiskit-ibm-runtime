# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Common functionality for account management."""

from urllib.parse import urlparse

import requests
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_platform_services import ResourceControllerV2

from ..utils.utils import is_crn


def get_iam_api_url(cloud_url: str) -> str:
    """Computes the IAM API URL for the given IBM Cloud URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://iam.{parsed_url.hostname}"


def get_global_search_api_url(cloud_url: str) -> str:
    """Compute the GlobalSearchV2 API URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://api.global-search-tagging.{parsed_url.hostname}"


def get_global_catalog_api_url(cloud_url: str) -> str:
    """Compute the GlobalCatalogV1 API URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://globalcatalog.{parsed_url.hostname}/api/v1"


def get_resource_controller_api_url(cloud_url: str) -> str:
    """Computes the Resource Controller API URL for the given IBM Cloud URL."""
    parsed_url = urlparse(cloud_url)
    return f"{parsed_url.scheme}://resource-controller.{parsed_url.hostname}"


def resolve_crn(channel: str, url: str, instance: str, token: str) -> list[str]:
    """Resolves the Cloud Resource Name (CRN) for the given cloud account."""
    if channel not in ["ibm_cloud", "ibm_quantum_platform"]:
        raise ValueError("CRN value can only be resolved for cloud accounts.")

    if is_crn(instance):
        # no need to resolve CRN value by name
        return [instance]
    else:
        with requests.Session() as session:
            # resolve CRN value based on the provided service name
            authenticator = IAMAuthenticator(token, url=get_iam_api_url(url))
            client = ResourceControllerV2(authenticator=authenticator)
            client.set_service_url(get_resource_controller_api_url(url))
            client.set_http_client(session)
            client.configure_service("resource_controller")
            list_response = client.list_resource_instances(name=instance)
            result = list_response.get_result()
            row_count = result["rows_count"]
            if row_count == 0:
                return []
            else:
                return [resource["crn"] for resource in result["resources"]]
