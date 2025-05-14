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
from typing import Optional, Literal, List, Dict
from urllib.parse import urlparse

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from ibm_platform_services import GlobalSearchV2
from requests.auth import AuthBase
from ..proxies import ProxyConfiguration
from ..utils.hgp import from_instance_format

from .exceptions import InvalidAccountError, CloudResourceNameResolutionError
from ..api.auth import QuantumAuth, CloudAuth
from ..utils import resolve_crn, cname_from_crn

AccountType = Optional[Literal["cloud", "legacy"]]
RegionType = Optional[Literal["us-east", "eu-de"]]
PlanType = Optional[List[str]]

ChannelType = Optional[
    Literal[
        "ibm_quantum_platform",
        "ibm_cloud",
        "ibm_quantum",
        "local",
    ]
]

IBM_QUANTUM_API_URL = "https://auth.quantum.ibm.com/api"
IBM_CLOUD_API_URL = "https://cloud.ibm.com"

# TODO fetch plan names instead of using this
# Pulled from IQP - I don't think this should be hard coded
PlanIdsByName = {
    "7f666d17-7893-47d8-bf9d-2b2389fc4dfc": "premium",
    "c8122eb7-fdb1-4746-841d-45bbc7678195": "dedicated",
    "91b2c828-2952-4f05-aed8-bedf92c6c480": "internal",
    "850b21a7-71de-4e53-9441-1abdd202f35d": "open",
    "53bde9d3-cdbb-46f5-a98f-60ebcadf7260": "flex",
    "5304b575-3cff-4455-90dc-ae4367762093": "standard",
}
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
            channel: Channel type, ``ibm_cloud``, ``ibm_quantum``, ``ibm_quantum_platform``.
            token: Account token to use.
            url: Authentication URL.
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
        self.account_id: str = None
        self.region: str = None
        self.plans_preference: List[str] = None

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
        if channel and url and channel == "ibm_quantum" and "-computing" in url:
            url = url.replace("-computing", "")
        token = data.get("token")
        instance = data.get("instance")
        verify = data.get("verify", True)
        private_endpoint = data.get("private_endpoint", False)
        account_id = data.get("account_id")
        region = data.get("region")
        plans_preference = data.get("plans_preference")
        return cls.create_account(
            channel=channel,
            url=url,
            token=token,
            instance=instance,
            proxies=proxies,
            verify=verify,
            private_endpoint=private_endpoint,
            account_id=account_id,
            region=region,
            plans_preference=plans_preference,
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
        account_id: Optional[str] = None,
        region: Optional[str] = None,
        plans_preference: Optional[List[str]] = None,
    ) -> "Account":
        """Creates an account for a specific channel."""
        if channel == "ibm_quantum":
            return QuantumAccount(
                url=url,
                token=token,
                instance=instance,
                proxies=proxies,
                verify=verify,
            )
        elif channel in ["ibm_cloud", "ibm_quantum_platform"]:
            return CloudAccount(
                url=url,
                token=token,
                instance=instance,
                proxies=proxies,
                verify=verify,
                private_endpoint=private_endpoint,
                account_id=account_id,
                region=region,
                plans_preference=plans_preference,
            )
        else:
            raise InvalidAccountError(
                f"Invalid `channel` value. Expected one of "
                f"{['ibm_cloud', 'ibm_quantum', 'ibm_quantum_platform']}, got '{channel}'."
            )

    def resolve_crn(self) -> None:
        """Resolves the corresponding unique Cloud Resource Name (CRN) for the given non-unique service
        instance name and updates the ``instance`` attribute accordingly.
        Relevant for "ibm_cloud" channel only."""
        pass

    def list_instances(  # type: ignore
        self, account_id: Optional[str] = None, include_plan_name: Optional[bool] = False
    ):
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

        self._assert_valid_channel(self.channel)
        self._assert_valid_token(self.token)
        self._assert_valid_url(self.url)
        self._assert_valid_instance(self.instance)
        self._assert_valid_proxies(self.proxies)
        return self

    @staticmethod
    def _assert_valid_channel(channel: ChannelType) -> None:
        """Assert that the channel parameter is valid."""
        if not (channel in ["ibm_cloud", "ibm_quantum", "ibm_quantum_platform"]):
            raise InvalidAccountError(
                f"Invalid `channel` value. Expected one of "
                f"['ibm_cloud', 'ibm_quantum', 'ibm_quantum_platform], got '{channel}'."
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


class QuantumAccount(Account):
    """Class that represents an account with channel 'ibm_quantum.'"""

    def __init__(
        self,
        token: str,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = True,
    ):
        """Account constructor.

        Args:
            token: Account token to use.
            url: Authentication URL.
            instance: Service instance to use.
            proxies: Proxy configuration.
            verify: Whether to verify server's TLS certificate.
        """
        super().__init__(token, instance, proxies, verify)
        resolved_url = url or IBM_QUANTUM_API_URL
        self.channel = "ibm_quantum"
        self.url = resolved_url

    def get_auth_handler(self) -> AuthBase:
        """Returns the Quantum authentication handler."""
        return QuantumAuth(access_token=self.token)

    @staticmethod
    def _assert_valid_instance(instance: str) -> None:
        """Assert that the instance name is valid for the given account type."""
        if instance is not None:
            try:
                from_instance_format(instance)
            except:
                raise InvalidAccountError(
                    f"Invalid `instance` value. Expected hub/group/project format, got {instance}"
                )


class CloudAccount(Account):
    """Class that represents an account with channel 'ibm_cloud'."""

    def __init__(
        self,
        token: str,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = True,
        private_endpoint: Optional[bool] = False,
        account_id: Optional[str] = None,
        region: Optional[str] = None,
        plans_preference: Optional[List[str]] = None,
    ):
        """Account constructor.

        Args:
            token: Account token to use.
            url: Authentication URL.
            instance: Service instance to use.
            proxies: Proxy configuration.
            verify: Whether to verify server's TLS certificate.
            private_endpoint: Connect to private API URL.
        """
        super().__init__(token, instance, proxies, verify)
        resolved_url = url or IBM_CLOUD_API_URL
        self.channel = "ibm_cloud"  # should this be ibm_quantum_platform?
        self.url = resolved_url
        self.private_endpoint = private_endpoint
        self.account_id = account_id
        self.region = region
        self.plans_preference = plans_preference

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
            channel="ibm_cloud",
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

    def list_instances(
        self, account_id: Optional[str] = None, include_plan_name: Optional[bool] = False
    ) -> List[Dict[str, str]]:
        """Retrieve all crns with the IBM Cloud Global Search API."""
        url = None
        is_staging = cname_from_crn(self.instance) == "staging"
        if is_staging:
            url = "https://iam.test.cloud.ibm.com"
        authenticator = IAMAuthenticator(self.token, url=url)
        client = GlobalSearchV2(authenticator=authenticator)
        if is_staging:
            client.set_service_url("https://api.global-search-tagging.test.cloud.ibm.com")
        search_cursor = None
        all_crns = []
        while True:
            result = client.search(
                query="service_name:quantum-computing",
                account_id=account_id,
                fields=["crn", "service_plan_unique_id", "name", "doc"],
                search_cursor=search_cursor,
                limit=100,
            ).get_result()
            crns = []
            items = result.get("items", [])
            for item in items:
                # don't add instances without backend allocation
                allocations = item.get("doc", {}).get("extensions")
                if allocations:
                    plan_name = None
                    if include_plan_name:
                        plan_name = PlanIdsByName.get(item.get("service_plan_unique_id"))
                    crns.append(
                        {
                            "crn": item.get("crn"),
                            "plan": plan_name,
                            "account_id": item.get("account_id"),
                            "name": item.get("name"),
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
