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

"""Account related classes and functions."""

from abc import abstractmethod
import logging
from typing import Optional, Literal, List, Dict, Any
from urllib.parse import urlparse

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from ibm_platform_services import GlobalSearchV2, GlobalCatalogV1
from requests.auth import AuthBase
from ..proxies import ProxyConfiguration

from .exceptions import InvalidAccountError, CloudResourceNameResolutionError
from ..api.auth import CloudAuth
from ..utils import (
    resolve_crn,
    get_iam_api_url,
    get_global_search_api_url,
    get_global_catalog_api_url,
)

AccountType = Optional[Literal["cloud", "legacy"]]
RegionType = Optional[Literal["us-east", "eu-de"]]
PlanType = Optional[List[str]]

ChannelType = Optional[
    Literal[
        "ibm_quantum_platform",
        "ibm_cloud",
        "local",
    ]
]

IBM_QUANTUM_PLATFORM_API_URL = "https://cloud.ibm.com"
IBM_CLOUD_API_URL = "https://cloud.ibm.com"

logger = logging.getLogger(__name__)


class Account:
    """Class that represents an account. This is an abstract class."""

    def __init__(
        self,
        token: str,
        instance: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = True,
    ):
        """Account constructor.

        Args:
            channel: Channel type,  ``ibm_quantum_platform``, ``ibm_cloud``.
            token: Account token to use.
            instance: Service instance to use.
            proxies: Proxy configuration.
            verify: Whether to verify server's TLS certificate.
        """
        self.channel: str = None
        self.url: str = None
        self.token = token
        self.instance = instance
        self.proxies = proxies
        self.verify = verify
        self.private_endpoint: bool = False
        self.region: str = None
        self.plans_preference: List[str] = None
        self.tags: List[str] = None

    def to_saved_format(self) -> dict:
        """Returns a dictionary that represents how the account is saved on disk."""
        result = {k: v for k, v in self.__dict__.items() if v is not None}
        if self.proxies:
            result["proxies"] = self.proxies.to_dict()
        return result

    @classmethod
    def from_saved_format(cls, data: dict) -> "Account":
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

    @classmethod
    def create_account(
        cls,
        channel: str,
        token: str,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = True,
        private_endpoint: Optional[bool] = False,
        region: Optional[str] = None,
        plans_preference: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> "Account":
        """Creates an account for a specific channel."""
        if channel in ["ibm_cloud", "ibm_quantum_platform"]:
            return CloudAccount(
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

    def resolve_crn(self) -> None:
        """Resolves the corresponding unique Cloud Resource Name (CRN) for the given non-unique service
        instance name and updates the ``instance`` attribute accordingly.
        Relevant for "ibm_cloud" channel only."""
        pass

    def list_instances(self) -> List[Dict[str, Any]]:  # type: ignore
        """Retrieve all crns with the IBM Cloud Global Search API."""
        pass

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

    def validate(self) -> "Account":
        """Validates the account instance.

        Raises:
            InvalidAccountError: if the account is invalid

        Returns:
            This Account instance.
        """

        self._assert_valid_preferences(self.region, self.plans_preference, self.tags)
        self._assert_valid_channel(self.channel)
        self._assert_valid_token(self.token)
        self._assert_valid_url(self.url)
        self._assert_valid_instance(self.instance)
        self._assert_valid_proxies(self.proxies)
        return self

    @staticmethod
    def _assert_valid_channel(channel: ChannelType) -> None:
        """Assert that the channel parameter is valid."""
        if not (channel in ["ibm_cloud", "ibm_quantum_platform"]):
            raise InvalidAccountError(
                f"Invalid `channel` value. Expected one of "
                f"['ibm_cloud', 'ibm_quantum_platform], got '{channel}'."
            )

    @staticmethod
    def _assert_valid_token(token: str) -> None:
        """Assert that the token is valid."""
        if not (isinstance(token, str) and len(token) > 0):
            raise InvalidAccountError(
                f"Invalid `token` value. Expected a non-empty string, got '{token}'."
            )

    @staticmethod
    def _assert_valid_url(url: str) -> None:
        """Assert that the URL is valid."""
        try:
            urlparse(url)
        except:
            raise InvalidAccountError(f"Invalid `url` value. Failed to parse '{url}' as URL.")

    @staticmethod
    def _assert_valid_proxies(config: ProxyConfiguration) -> None:
        """Assert that the proxy configuration is valid."""
        if config is not None:
            config.validate()

    @staticmethod
    @abstractmethod
    def _assert_valid_instance(instance: str) -> None:
        """Assert that the instance name is valid for the given account type."""
        pass

    @staticmethod
    @abstractmethod
    def _assert_valid_preferences(
        region: str, plans_preference: List[str], tags: List[str]
    ) -> None:
        """Assert that the account preferences are valid."""
        pass


class CloudAccount(Account):
    """Class that represents an account with channel 'ibm_cloud' or 'ibm_quantum_platform'."""

    def __init__(
        self,
        token: str,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = True,
        private_endpoint: Optional[bool] = False,
        region: Optional[str] = None,
        plans_preference: Optional[List[str]] = None,
        channel: Optional[str] = "ibm_quantum_platform",
        tags: Optional[str] = None,
    ):
        """Account constructor.

        Args:
            token: Account token to use.
            url: Authentication URL.
            instance: Service instance to use.
            proxies: Proxy configuration.
            verify: Whether to verify server's TLS certificate.
            private_endpoint: Connect to private API URL.
            region: Set a region preference. Accepted values are ``us-east`` or ``eu-de``.
            plans_preference: A list of account types, ordered by preference.
            channel: Channel identifier. Accepted values are ``ibm_cloud`` or ``ibm_quantum_platform``.
                Defaults to ``ibm_quantum_platform``.
            tags: List of instance tags.
        """
        super().__init__(token, instance, proxies, verify)
        resolved_url = url or (
            IBM_CLOUD_API_URL if channel == "ibm_cloud" else IBM_QUANTUM_PLATFORM_API_URL
        )
        self.channel = channel
        self.url = resolved_url
        self.private_endpoint = private_endpoint
        self.region = region
        self.plans_preference = plans_preference
        self.tags = tags

    def get_auth_handler(self) -> AuthBase:
        """Returns the Cloud authentication handler."""
        return CloudAuth(api_key=self.token, crn=self.instance, private=self.private_endpoint)

    def resolve_crn(self) -> None:
        """Resolves the corresponding unique Cloud Resource Name (CRN) for the given non-unique service
        instance name and updates the ``instance`` attribute accordingly.

        No-op if ``instance`` attribute is set to a Cloud Resource Name (CRN).

        Raises:
            CloudResourceNameResolutionError: if CRN value cannot be resolved.
        """
        crn = resolve_crn(
            channel=self.channel,
            url=self.url,
            token=self.token,
            instance=self.instance,
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

    def list_instances(self) -> List[Dict[str, Any]]:
        """Retrieve all crns with the IBM Cloud Global Search API."""
        iam_url = get_iam_api_url(self.url)
        authenticator = IAMAuthenticator(self.token, url=iam_url)
        client = GlobalSearchV2(authenticator=authenticator)
        catalog = GlobalCatalogV1(authenticator=authenticator)
        client.set_service_url(get_global_search_api_url(self.url))
        catalog.set_service_url(get_global_catalog_api_url(self.url))
        search_cursor = None
        all_crns = []
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
                ).get_result()
            except:
                raise InvalidAccountError("Unable to retrieve instances.")
            crns = []
            items = result.get("items", [])
            for item in items:
                # don't add instances without backend allocation
                allocations = item.get("doc", {}).get("extensions")
                if allocations:
                    catalog_result = catalog.get_catalog_entry(
                        id=item.get("service_plan_unique_id")
                    ).get_result()
                    plan_name = (
                        catalog_result.get("overview_ui", {}).get("en", {}).get("display_name", "")
                    )
                    crns.append(
                        {
                            "crn": item.get("crn"),
                            "plan": plan_name.lower(),
                            "name": item.get("name"),
                            "tags": item.get("tags"),
                        }
                    )

            all_crns.extend(crns)
            search_cursor = result.get("search_cursor")
            if not search_cursor:
                break
        return all_crns

    @staticmethod
    def _assert_valid_instance(instance: str) -> None:
        """Assert that the instance name is valid for the given account type."""
        if instance and not isinstance(instance, str):
            raise InvalidAccountError(
                f"Invalid `instance` value. Expected an IBM Cloud crn, got '{instance}' instead. "
            )

    @staticmethod
    def _assert_valid_preferences(
        region: str, plans_preference: List[str], tags: List[str]
    ) -> None:
        """Assert that the account preferences are valid."""
        if region and (region not in ["us-east", "eu-de"] or not isinstance(region, str)):
            raise InvalidAccountError(
                f"Invalid `region` value. Expected `us-east` or `eu-de`, got '{region}' instead. "
            )
        if plans_preference and not isinstance(plans_preference, list):
            raise InvalidAccountError(
                "Invalid `plans_preference` value. Expected a list of strings, "
                f"got '{plans_preference}' instead."
            )
        if tags and not isinstance(tags, list):
            raise InvalidAccountError(
                "Invalid `tags` value. Expected a list of strings. " f"got '{tags}' instead."
            )
