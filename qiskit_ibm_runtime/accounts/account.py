# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Account related classes and functions."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Literal, TypeAlias
from urllib.parse import urlparse

from ibm_cloud_sdk_core import ApiException
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_platform_services import GlobalCatalogV1, GlobalSearchV2

from ..api.auth import CloudAuth
from ..proxies import ProxyConfiguration
from .exceptions import CloudResourceNameResolutionError, InvalidAccountError
from .utils import (
    get_global_catalog_api_url,
    get_global_search_api_url,
    get_iam_api_url,
    resolve_crn,
)

if TYPE_CHECKING:
    from requests.auth import AuthBase

AccountType: TypeAlias = Literal["cloud", "legacy"] | None
RegionType: TypeAlias = Literal["us-east", "eu-de"] | None
PlanType: TypeAlias = list[str] | None

ChannelType: TypeAlias = Literal["ibm_quantum_platform", "ibm_cloud", "local"] | None

IBM_QUANTUM_PLATFORM_API_URL = "https://cloud.ibm.com"

logger = logging.getLogger(__name__)


class Account:
    """Class that represents an account with channel 'ibm_cloud' or 'ibm_quantum_platform'.

    Args:
        token: Account token to use.
        url: Authentication URL.
        instance: Service instance to use.
        proxies: Proxy configuration.
        verify: Whether to verify server's TLS certificate.
        private_endpoint: Connect to private API URL.
        region: Set a region preference. Accepted values are ``us-east`` or ``eu-de``.
        plans_preference: A list of account types, ordered by preference.
        channel: Channel identifier. Accepted values are ``ibm_cloud`` or
            ``ibm_quantum_platform``. Defaults to ``ibm_quantum_platform``.
        tags: List of instance tags.
    """

    def __init__(
        self,
        token: str,
        url: str | None = None,
        instance: str | None = None,
        proxies: ProxyConfiguration | None = None,
        verify: bool | None = True,
        private_endpoint: bool | None = False,
        region: str | None = None,
        plans_preference: list[str] | None = None,
        channel: str | None = "ibm_quantum_platform",
        tags: list[str] | None = None,
    ):
        self.token = token
        self.instance = instance
        self.proxies = proxies
        self.verify = verify
        self.channel = channel
        self.url = url or IBM_QUANTUM_PLATFORM_API_URL
        self.private_endpoint = private_endpoint
        self.region = region
        self.plans_preference = plans_preference
        self.tags = tags

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Account):
            return False
        return all(
            [
                self.channel == other.channel,
                self.token == other.token,
                self.url == other.url,
                self.instance == other.instance,
                self.proxies == other.proxies,
                self.verify == other.verify,
            ]
        )

    @classmethod
    def create_account(
        cls,
        channel: str,
        token: str,
        url: str | None = None,
        instance: str | None = None,
        proxies: ProxyConfiguration | None = None,
        verify: bool | None = True,
        private_endpoint: bool | None = False,
        region: str | None = None,
        plans_preference: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Account:
        """Creates an account for a specific channel."""
        if channel in ["ibm_cloud", "ibm_quantum_platform"]:
            return cls(
                url=url,
                token=token,
                instance=instance,
                proxies=proxies,
                verify=verify,
                private_endpoint=private_endpoint,
                region=region,
                plans_preference=plans_preference,
                channel=channel,
                tags=tags,
            )
        else:
            raise InvalidAccountError(
                f"Invalid `channel` value. Expected one of "
                f"{['ibm_cloud', 'ibm_quantum_platform']}, got '{channel}'."
            )

    @classmethod
    def from_saved_format(cls, data: dict) -> Account:
        """Creates an account instance from data saved on disk."""
        channel = data.get("channel")
        proxies = data.get("proxies")
        proxies = ProxyConfiguration(**proxies) if proxies else None
        url = data.get("url")
        token = data.get("token")
        instance = data.get("instance")
        verify = data.get("verify", True)
        private_endpoint = data.get("private_endpoint", False)
        region = data.get("region")
        plans_preference = data.get("plans_preference")
        tags = data.get("tags")
        return cls.create_account(
            channel=channel,
            url=url,
            token=token,
            instance=instance,
            proxies=proxies,
            verify=verify,
            private_endpoint=private_endpoint,
            region=region,
            plans_preference=plans_preference,
            tags=tags,
        )

    def to_saved_format(self) -> dict:
        """Returns a dictionary that represents how the account is saved on disk."""
        result = {k: v for k, v in self.__dict__.items() if v is not None}
        if self.proxies:
            result["proxies"] = self.proxies.to_dict()
        return result

    def get_auth_handler(self) -> AuthBase:
        """Returns the Cloud authentication handler."""
        return CloudAuth(
            api_key=self.token,
            crn=self.instance,
            private=self.private_endpoint,
            proxies=self.proxies,
            verify=self.verify,
        )

    def _get_proxies_kwargs(self) -> dict:
        proxies_kwargs = {}
        if self.proxies is not None:
            proxies_kwargs = self.proxies.to_request_params()
        return proxies_kwargs

    def get_iam_authentificator(self) -> IAMAuthenticator:
        """Return the configured IAM Authentification service."""
        iam_url = os.environ.get("IAM_URL") or get_iam_api_url(self.url)
        proxies_kwargs = self._get_proxies_kwargs()
        return IAMAuthenticator(
            apikey=self.token,
            url=iam_url,
            disable_ssl_verification=not self.verify,
            **proxies_kwargs,
        )

    def resolve_crn(self) -> None:
        """Resolves the corresponding CRN, updating the ``instance`` attribute accordingly.

        Resolves the corresponding unique Cloud Resource Name (CRN) for the given non-unique
        service instance name and updates the ``instance`` attribute accordingly.

        No-op if ``instance`` attribute is set to a Cloud Resource Name (CRN).

        Raises:
            CloudResourceNameResolutionError: if CRN value cannot be resolved.
        """
        crn = resolve_crn(
            channel=self.channel,
            url=self.url,
            token=self.token,
            instance=self.instance,
            proxies_kwargs=self._get_proxies_kwargs(),
            verify=True if self.verify is not False else False,
        )
        if len(crn) == 0:
            raise CloudResourceNameResolutionError(
                f"Failed to resolve CRN value for the provided service name {self.instance}."
            )

        if len(crn) > 1:
            # handle edge-case where multiple service instances with the same name exist
            logger.warning(
                "Multiple CRN values found for service name %s:",
                crn[0],
            )

        # overwrite with CRN value
        self.instance = crn[0]

    def list_instances(self) -> list[dict[str, Any]]:
        """Retrieve all crns with the IBM Cloud Global Search API."""
        # Bypass calling Global Search and Global Catalog.
        if os.environ.get("QISKIT_FUNCTIONS_EXPERIMENTAL"):
            return [
                {
                    "crn": self.instance,
                    "plan": "plan",
                    "name": "name",
                    "tags": [],
                    "pricing_type": "unknown",
                }
            ]

        authenticator = self.get_iam_authentificator()
        client = GlobalSearchV2(authenticator=authenticator)
        catalog = GlobalCatalogV1(authenticator=authenticator)

        # Prepare the services.
        client.set_service_url(get_global_search_api_url(self.url))
        catalog.set_service_url(get_global_catalog_api_url(self.url))
        client.configure_service("global_search")
        catalog.configure_service("global_catalog")

        search_cursor = None
        all_crns = []
        proxies_kwargs = self._get_proxies_kwargs()
        while True:
            try:
                result = client.search(
                    query="service_name:quantum-computing",
                    fields=[
                        "crn",
                        "service_plan_unique_id",
                        "name",
                        "doc",
                        "tags",
                    ],
                    search_cursor=search_cursor,
                    limit=100,
                    verify=self.verify,
                    **proxies_kwargs,
                ).get_result()
            except Exception as ex:
                raise InvalidAccountError(
                    "Unable to retrieve instances. "
                    "Please check that you are using a valid API token."
                ) from ex
            crns = []
            items = result.get("items", [])
            for item in items:
                # don't add instances without backend allocation
                allocations = item.get("doc", {}).get("extensions")
                if allocations:
                    try:
                        catalog_result = catalog.get_catalog_entry(
                            id=item.get("service_plan_unique_id"),
                            verify=self.verify,
                            **proxies_kwargs,
                        ).get_result()
                        plan_name = (
                            catalog_result.get("overview_ui", {})
                            .get("en", {})
                            .get("display_name", "")
                        )
                        pricing_type = (
                            catalog_result.get("metadata", {}).get("pricing", {}).get("type", "")
                        )
                    except (ApiException, KeyError):
                        # The catalog does not allow querying archived entries, returning 403.
                        logger.warning(
                            "The plan and pricing type for instance %s could not be retrieved.",
                            item.get("crn"),
                        )
                        plan_name = "unknown"
                        pricing_type = "unknown"
                    crns.append(
                        {
                            "crn": item.get("crn"),
                            "plan": plan_name.lower(),
                            "name": item.get("name"),
                            "tags": item.get("tags"),
                            "pricing_type": pricing_type.lower(),
                        }
                    )

            all_crns.extend(crns)
            search_cursor = result.get("search_cursor")
            if not search_cursor:
                break
        return all_crns

    def validate(self) -> Account:
        """Validates the account instance.

        Raises:
            InvalidAccountError: if the account is invalid

        Returns:
            This Account instance.
        """
        # Validate preferences.
        if self.region and (
            self.region not in ["us-east", "eu-de"] or not isinstance(self.region, str)
        ):
            raise InvalidAccountError(
                f"Invalid `region` value. Expected `us-east` or `eu-de`, got '{self.region}' "
                "instead."
            )
        if self.plans_preference and not isinstance(self.plans_preference, list):
            raise InvalidAccountError(
                "Invalid `plans_preference` value. Expected a list of strings, "
                f"got '{self.plans_preference}' instead."
            )
        if self.tags and not isinstance(self.tags, list):
            raise InvalidAccountError(
                f"Invalid `tags` value. Expected a list of strings. got '{self.tags}' instead."
            )

        # Validate channel, token, url, instance.
        if self.channel not in ["ibm_cloud", "ibm_quantum_platform"]:
            raise InvalidAccountError(
                f"Invalid `channel` value. Expected one of "
                f"['ibm_cloud', 'ibm_quantum_platform], got '{self.channel}'."
            )
        if not (isinstance(self.token, str) and len(self.token) > 0):
            raise InvalidAccountError(
                f"Invalid `token` value. Expected a non-empty string, got '{self.token}'."
            )
        try:
            urlparse(self.url)
        except:  # noqa: E722 bare-except
            raise InvalidAccountError(f"Invalid `url` value. Failed to parse '{self.url}' as URL.")
        if self.instance and not isinstance(self.instance, str):
            raise InvalidAccountError(
                f"Invalid `instance` value. Expected an IBM Cloud crn, got '{self.instance}'"
                "instead. "
            )

        # Validate proxies.
        if self.proxies is not None:
            self.proxies.validate()

        return self
