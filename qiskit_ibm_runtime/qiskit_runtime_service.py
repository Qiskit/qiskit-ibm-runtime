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

"""Qiskit runtime service."""

import logging
import warnings
from datetime import datetime
from typing import Dict, Callable, Optional, Union, List, Any, Type, Sequence, Tuple

from qiskit.providers.backend import BackendV2 as Backend
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends

from qiskit_ibm_runtime import ibm_backend
from .proxies import ProxyConfiguration
from .utils import is_crn
from .utils.backend_decoder import configuration_from_server_data

from .accounts import AccountManager, Account, ChannelType, RegionType, PlanType
from .api.clients import VersionClient
from .api.clients.runtime import RuntimeClient
from .api.exceptions import RequestsApiError
from .exceptions import IBMInputValueError
from .exceptions import IBMRuntimeError, RuntimeProgramNotFound, RuntimeJobNotFound
from .utils.result_decoder import ResultDecoder
from .runtime_job import RuntimeJob
from .runtime_job_v2 import RuntimeJobV2
from .utils import validate_job_tags
from .api.client_parameters import ClientParameters
from .runtime_options import RuntimeOptions
from .ibm_backend import IBMBackend
from .models import QasmBackendConfiguration

logger = logging.getLogger(__name__)

SERVICE_NAME = "runtime"


class QiskitRuntimeService:
    """Class for interacting with the Qiskit Runtime service."""

    def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def]
        channel = kwargs.get("channel", None)
        if channel == "local":
            # pylint: disable=import-outside-toplevel
            from .fake_provider.local_service import QiskitRuntimeLocalService

            return super().__new__(QiskitRuntimeLocalService)
        else:
            return super().__new__(cls)

    def __init__(
        self,
        channel: Optional[ChannelType] = None,
        token: Optional[str] = None,
        url: Optional[str] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        instance: Optional[str] = None,
        proxies: Optional[dict] = None,
        verify: Optional[bool] = None,
        private_endpoint: Optional[bool] = None,
        url_resolver: Optional[Callable[[str, str, Optional[bool], str], str]] = None,
        region: Optional[str] = None,
        plans_preference: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """QiskitRuntimeService constructor.

        An account is selected in the following order:
            - If a ``filename`` is specified, account details will be loaded from ``filename``,
                else they will be loaded from the default configuration file.
            - If ``name`` is specified, the corresponding account details will be loaded from
                the configuration file, including ``channel``, ``token``, ``instance``, ``region``,
                ``plans_preference`, and the advanced configuration parameters: ``url``,
                ``url_resolver``, ``private_endpoint``,  ``verify``, and  ``proxies``.
            - If ``channel`` is specified, the default account details for that channel will be
                loaded from the configuration file, else, the account details will be loaded
                from the ``default_channel`` defined in the configuration file.
            - Any loaded details will be overwritten by the corresponding parameter in the
                service constructor.

        The minimum required information for service authentication to a non-local channel is the
        ``token``. The ``local`` channel doesn't require authentication.
        For the ``"ibm_cloud"`` and ``"ibm_quantum_platform"`` channels it is recommended
        to provide the relevant ``instance`` to minimize API calls. If an ``instance`` is not defined,
        the service will fetch all instances accessible within the account, filtered by
        ``region``, ``plans_preference``, and ``tags``.

        Args:
            Optional[ChannelType] channel: Channel type. ``ibm_cloud``,
                ``ibm_quantum_platform`` or ``local``.
                If ``local`` is selected, the local testing mode will be used, and
                primitive queries will run on a local simulator. For more details, check the
                `Qiskit Runtime local testing mode
                <https://quantum.cloud.ibm.com/docs/guides/local-testing-mode>`_  documentation.
            Optional[str] token: IBM Cloud API key.
            Optional[str] url: The API URL.
                Defaults to https://quantum-computing.cloud.ibm.com (``ibm_cloud``),
                https://quantum.cloud.ibm.com  (``ibm_quantum_platform``) or
            Optional[str] filename: Full path of the file where the account is created.
                Default: _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
            Optional[str] name: Name of the account to load.
            Optional[str] instance: The service instance to use.
                For ``ibm_cloud`` and ``ibm_quantum_platform``, this is the Cloud Resource
                Name (CRN) or the service name. If set, it will define a default instance for
                service instantiation, if not set, the service will fetch all instances accessible
                within the account.
            Optional[dict] proxies: Proxy configuration. Supported optional keys are
                ``urls`` (a dictionary mapping protocol or protocol and host to the URL of the proxy,
                documented at https://requests.readthedocs.io/en/latest/api/#requests.Session.proxies),
                ``username_ntlm``, ``password_ntlm`` (username and password to enable NTLM user
                authentication)
            Optional[bool] verify: Whether to verify the server's TLS certificate.
            Optional[bool] private_endpoint: Connect to private API URL.
            Optional[Callable] url_resolver: Function used to resolve the runtime url.
            Optional[str] region: Set a region preference. Accepted values are ``us-east`` or ``eu-de``.
                An instance with this region will be prioritized if an instance is not passed in.
            Optional[List[str]] plans_preference: A list of account types, ordered by preference.
                An instance with the first value in the list will be prioritized if an instance
                is not passed in.
            Optional[List[str]] tags: Set a list of tags to filter available instances.

        Returns:
            An instance of QiskitRuntimeService or QiskitRuntimeLocalService for local channel.

        Raises:
            IBMInputValueError: If an input is invalid.
        """
        super().__init__()
        self._all_instances: List[Dict[str, Any]] = []
        self._saved_instances: List[str] = []
        self._account = self._discover_account(
            token=token,
            url=url,
            instance=instance,
            channel=channel,
            filename=filename,
            name=name,
            proxies=ProxyConfiguration(**proxies) if proxies else None,
            verify=verify,
        )

        if private_endpoint is not None:
            self._account.private_endpoint = private_endpoint

        self._client_params = ClientParameters(
            channel=self._account.channel,
            token=self._account.token,
            url=self._account.url,
            instance=self._account.instance,
            proxies=self._account.proxies,
            verify=self._account.verify,
            private_endpoint=self._account.private_endpoint,
            url_resolver=url_resolver,
        )

        self._channel = self._account.channel
        self._url_resolver = url_resolver
        self._backend_configs: Dict[str, QasmBackendConfiguration] = {}

        self._default_instance = False
        self._active_api_client = RuntimeClient(self._client_params)
        self._backends_list: List[Dict[str, Any]] = []
        self._backend_instance_groups: List[Dict[str, Any]] = []
        self._region = region or self._account.region
        self._plans_preference = plans_preference or self._account.plans_preference
        self._tags = tags or self._account.tags
        if self._account.instance:
            self._default_instance = True
        if instance is not None:
            self._api_clients = {instance: RuntimeClient(self._client_params)}
        else:
            self._api_clients = {}
            instance_backends = self._resolve_cloud_instances(instance)
            for inst, _ in instance_backends:
                self._get_or_create_cloud_client(inst)

    def _discover_backends_from_instance(self, instance: str) -> List[str]:
        """Retrieve all backends from the given instance."""
        # TODO refactor this, this is the slowest part
        # ntc 5779 would make things a lot faster - get list of backends
        # from global search API call
        try:
            if instance != self._active_api_client._instance:
                if instance in self._api_clients:
                    self._active_api_client = self._api_clients[instance]
                else:
                    new_client = self._create_new_cloud_api_client(instance)
                    self._api_clients.update({instance: new_client})
                    self._active_api_client = new_client
            self._backends_list = self._active_api_client.list_backends()
            return [backend["name"] for backend in self._backends_list]
        # On staging there some invalid instances returned that 403 when retrieving backends
        except Exception:  # pylint: disable=broad-except
            logger.warning("Invalid instance %s", instance)
            return []

    def _create_new_cloud_api_client(self, instance: str) -> RuntimeClient:
        """Create a new api_client given an instance."""
        self._client_params = ClientParameters(
            channel=self._account.channel,
            token=self._account.token,
            url=self._account.url,
            instance=instance,
            proxies=self._account.proxies,
            verify=self._account.verify,
            private_endpoint=self._account.private_endpoint,
            url_resolver=self._url_resolver,
        )
        return RuntimeClient(self._client_params)

    def _filter_instances_by_saved_preferences(self) -> None:
        """Filter instances by saved region and plan preferences."""
        if self._tags:
            self._backend_instance_groups = [
                d
                for d in self._backend_instance_groups
                if all(tag.lower() in d["tags"] for tag in self._tags)
            ]

        if self._region:
            self._backend_instance_groups = [
                d for d in self._backend_instance_groups if self._region in d["crn"]
            ]

        if self._plans_preference:
            plans = [plan.lower() for plan in self._plans_preference]
            # We should filter out the other instances, minimize api calls
            filtered_groups = [
                group for group in self._backend_instance_groups if group["plan"] in plans
            ]

            self._backend_instance_groups = sorted(
                filtered_groups, key=lambda d: plans.index(d["plan"])
            )

        if not self._backend_instance_groups:
            error_string = ""
            if self._tags:
                error_string += f"tags: {self._tags}, "
            if self._region:
                error_string += f"region: {self._region}, "
            if self._plans_preference:
                error_string += f"plan: {self._plans_preference}"
            raise IBMInputValueError(
                "No matching instances found for the following filters:",
                f"{error_string}.",
            )

    def _discover_account(
        self,
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        channel: Optional[ChannelType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = None,
    ) -> Account:
        """Discover account for ibm_cloud and ibm_quantum_platform channels."""
        account = None
        verify_ = verify or True
        if name:
            if filename:
                if any([channel, token, url]):
                    logger.warning(
                        "Loading account from file %s with name %s. Any input "
                        "'channel', 'token' or 'url' are ignored.",
                        filename,
                        name,
                    )
            else:
                if any([channel, token, url]):
                    logger.warning(
                        "Loading account with name %s. Any input "
                        "'channel', 'token' or 'url' are ignored.",
                        name,
                    )
            account = AccountManager.get(filename=filename, name=name)
        elif channel:
            if channel and channel not in ["ibm_cloud", "ibm_quantum_platform"]:
                raise ValueError("'channel' can only be 'ibm_cloud', or 'ibm_quantum_platform")
            if token:
                account = Account.create_account(
                    channel=channel,
                    token=token,
                    url=url,
                    instance=instance,
                    proxies=proxies,
                    verify=verify_,
                )
            else:
                if url:
                    logger.warning("Loading default %s account. Input 'url' is ignored.", channel)
                account = AccountManager.get(filename=filename, name=name, channel=channel)
        elif any([token, url]):
            # Let's not infer based on these attributes as they may change in the future.
            raise ValueError(
                "'channel' is required if 'token', or 'url' is specified but 'name' is not."
            )

        # channel is not defined yet, get it from the AccountManager
        if account is None:
            account = AccountManager.get(filename=filename)
        if instance:
            account.instance = instance
        if proxies:
            account.proxies = proxies
        if verify is not None:
            account.verify = verify

        # if instance is a name, change it to crn format
        if (
            account.channel in ["ibm_cloud", "ibm_quantum_platform"]
            and account.instance
            and not is_crn(account.instance)
        ):
            account.instance = self._get_crn_from_instance_name(
                account=account, instance=account.instance
            )

        # ensure account is valid, fail early if not
        account.validate()

        return account

    def _get_crn_from_instance_name(self, account: Account, instance: str) -> str:
        """Get the crn from the instance service name."""

        if not self._all_instances:
            self._all_instances = account.list_instances()
        matching_instances = [item for item in self._all_instances if item["name"] == instance]
        if matching_instances:
            if len(matching_instances) > 1:
                logger.warning("Multiple instances found. Using all matching instances.")
                # If there are multiple instances, save them
                self._saved_instances = [inst["crn"] for inst in matching_instances]
            return matching_instances[0]["crn"]
        else:
            raise IBMInputValueError(
                f"The instance specified ({instance}) is not a valid " "instance name."
            )

    @staticmethod
    def _check_api_version(params: ClientParameters) -> Dict[str, Union[bool, str]]:
        """Check the version of the remote server in a set of client parameters for all channels.

        Args:
            params: Parameters used for server connection.

        Returns:
            A dictionary with version information.
        """
        version_finder = VersionClient(url=params.url, **params.connection_parameters())
        return version_finder.version()

    def _get_api_client(
        self,
        instance: Optional[str] = None,
    ) -> RuntimeClient:
        """Return the saved api client for a given instance for all channels.
        If no instance is provided, return the current active api client.

        Args:
            instance: IBM Cloud account CRN

        Returns:
            An instance of ``RuntimeClient`` that matches the specified instance.

        Raises:
            IBMInputValueError: If no saved api client matches the given instance.
        """
        if instance is None:
            return self._active_api_client
        else:
            client = self._api_clients.get(instance, None)
            if client is None:
                raise IBMInputValueError(f"No API client found for given instance: {instance}")
            return client

    def _get_api_clients(self) -> dict[str, RuntimeClient]:
        """Return dictionary of saved api clients identified by their corresponding instance
        for all channels.

        Returns:
            An dictionary of {instance: RuntimeClient}
        """
        return self._api_clients

    # pylint: disable=arguments-differ
    def backends(
        self,
        name: Optional[str] = None,
        min_num_qubits: Optional[int] = None,
        instance: Optional[str] = None,
        dynamic_circuits: Optional[bool] = None,
        filters: Optional[Callable[["ibm_backend.IBMBackend"], bool]] = None,
        *,
        use_fractional_gates: Optional[bool] = False,
        **kwargs: Any,
    ) -> List["ibm_backend.IBMBackend"]:
        """Return all backends accessible via this account, subject to optional filtering.

        Args:
            name: Backend name to filter by.
            min_num_qubits: Minimum number of qubits the backend has to have.
            instance: IBM Cloud account CRN
            dynamic_circuits: Filter by whether the backend supports dynamic circuits.
            filters: More complex filters, such as lambda functions.
                For example::

                    QiskitRuntimeService.backends(
                        filters=lambda b: b.max_shots > 50000
                    )
                    QiskitRuntimeService.backends(
                        filters=lambda x: ("rz" in x.basis_gates )
                    )
            use_fractional_gates: Set True to allow for the backends to include
                fractional gates. Currently this feature cannot be used
                simultaneously with dynamic circuits, PEC, PEA, or gate
                twirling.  When this flag is set, control flow instructions are
                automatically removed from the backend.
                When you use a dynamic circuits feature (e.g. ``if_else``) in your
                algorithm, you must disable this flag to create executable ISA circuits.
                This flag might be modified or removed when our backend
                supports dynamic circuits and fractional gates simultaneously.
                If ``None``, then both fractional gates and control flow operations are
                included in the backends.

            **kwargs: Simple filters that require a specific value for an attribute in
                backend configuration or status.
                Examples::

                    # Get the operational real backends
                    QiskitRuntimeService.backends(simulator=False, operational=True)

                    # Get the backends with at least 127 qubits
                    QiskitRuntimeService.backends(min_num_qubits=127)

                    # Get the backends that support OpenPulse
                    QiskitRuntimeService.backends(open_pulse=True)

                For the full list of backend attributes, see the `IBMBackend` class documentation
                <https://quantum.cloud.ibm.com/docs/api/qiskit/1.4/providers_models>

        Returns:
            The list of available backends that match the filter.

        Raises:
            IBMInputValueError: If an input is invalid.
            QiskitBackendNotFoundError: If the backend is not in any instance.
        """
        if dynamic_circuits is True and use_fractional_gates:
            raise QiskitBackendNotFoundError(
                "Currently fractional_gates and dynamic_circuits feature cannot be "
                "simulutaneously enabled. Consider disabling one or the other."
            )

        backends: List[IBMBackend] = []

        unique_backends = set()
        instance_backends = self._resolve_cloud_instances(instance)
        for inst, backends_available in instance_backends:
            if name:
                if name not in backends_available:
                    continue
                backends_available = [name]
            for backend_name in backends_available:
                if backend_name in unique_backends:
                    continue
                unique_backends.add(backend_name)
                self._get_or_create_cloud_client(inst)
                if backend := self._create_backend_obj(
                    backend_name,
                    instance=inst,
                    use_fractional_gates=use_fractional_gates,
                ):
                    backends.append(backend)
        if name:
            kwargs["backend_name"] = name
        if min_num_qubits:
            backends = list(
                filter(lambda b: b.configuration().n_qubits >= min_num_qubits, backends)
            )
        if dynamic_circuits is not None:
            backends = list(
                filter(
                    lambda b: ("qasm3" in getattr(b.configuration(), "supported_features", []))
                    == dynamic_circuits,
                    backends,
                )
            )

        # Set fractional gate flag for use when loading properties or refreshing backend.
        for backend in backends:
            backend.options.use_fractional_gates = use_fractional_gates
        return filter_backends(backends, filters=filters, **kwargs)

    def _resolve_cloud_instances(self, instance: Optional[str]) -> List[Tuple[str, List[str]]]:
        if instance:
            if not is_crn(instance):
                instance = self._get_crn_from_instance_name(self._account, instance)
                if not instance:
                    raise IBMInputValueError(f"{instance} is not a valid instance.")
            # if an instance name is passed in and there are multiple crns,
            # return all matching crns (stored in self._saved_instances)
            if self._saved_instances:
                return [
                    (inst, self._discover_backends_from_instance(inst))
                    for inst in self._saved_instances
                ]
            return [(instance, self._discover_backends_from_instance(instance))]
        if self._default_instance:
            # if an instance name is passed in and there are multiple crns,
            # return all matching crns (stored in self._saved_instances)
            default_crn = self._account.instance
            if self._saved_instances:
                return [
                    (inst, self._discover_backends_from_instance(inst))
                    for inst in self._saved_instances
                ]
            return [(default_crn, self._discover_backends_from_instance(default_crn))]
        if not self._all_instances:
            self._all_instances = self._account.list_instances()
            logger.warning(
                "Default instance not set. Searching all available instances.",
            )
        if not self._backend_instance_groups:
            self._backend_instance_groups = [
                {
                    "crn": inst["crn"],
                    "plan": inst["plan"],
                    "backends": self._discover_backends_from_instance(inst["crn"]),
                    "tags": inst["tags"],
                }
                for inst in self._all_instances
            ]
            self._filter_instances_by_saved_preferences()
        return [(inst["crn"], inst["backends"]) for inst in self._backend_instance_groups]

    def _get_or_create_cloud_client(self, instance: str) -> None:
        """Find relevant cloud client for a given instance and set active api client."""
        if instance != self._active_api_client._instance:
            client = self._api_clients.get(instance)
            if client is None:
                client = self._create_new_cloud_api_client(instance)
                self._api_clients[instance] = client
            self._active_api_client = client

    def _create_backend_obj(
        self,
        backend_name: str,
        instance: Optional[str],
        use_fractional_gates: Optional[bool],
    ) -> IBMBackend:
        """Given a backend configuration return the backend object.

        Args:
            backend_name: Name of backend to instantiate.
            instance: the current CRN.
            use_fractional_gates: Set True to allow for the backends to include
                fractional gates, False to include control flow operations, and
                None to include both fractional gates and control flow
                operations.  See :meth:`~.QiskitRuntimeService.backends` for
                further details.

        Returns:
            A backend object.
        """
        try:
            if backend_name in self._backend_configs:
                config = self._backend_configs[backend_name]
                # if cached config does not match use_fractional_gates
                if (
                    use_fractional_gates
                    and "rzz" not in config.basis_gates
                    or not use_fractional_gates
                    and "rzz" in config.basis_gates
                ):
                    config = configuration_from_server_data(
                        raw_config=self._active_api_client.backend_configuration(backend_name),
                        instance=instance,
                        use_fractional_gates=use_fractional_gates,
                    )
                    self._backend_configs[backend_name] = config

            else:
                config = configuration_from_server_data(
                    raw_config=self._active_api_client.backend_configuration(backend_name),
                    instance=instance,
                    use_fractional_gates=use_fractional_gates,
                )
                # I know we have a configuration_registry in the api client
                # but that doesn't work with new IQP since we different api clients are being used

                self._backend_configs[backend_name] = config
        except Exception as ex:  # pylint: disable=broad-except
            logger.warning("Unable to create configuration for %s. %s ", backend_name, ex)
            return None

        if config:
            return ibm_backend.IBMBackend(
                instance=instance,
                configuration=config,
                service=self,
                api_client=self._active_api_client,
            )
        return None

    def active_account(self) -> Optional[Dict[str, str]]:
        """Return the IBM Quantum account currently in use for the session.

        Returns:
            A dictionary with information about the account currently in the session.
        """
        return self._account.to_saved_format()

    @staticmethod
    def delete_account(
        filename: Optional[str] = None,
        name: Optional[str] = None,
        channel: Optional[ChannelType] = None,
    ) -> bool:
        """Delete a saved account from disk.

        Args:
            filename: Name of file from which to delete the account.
            name: Name of the saved account to delete.
            channel: Channel type of the default account to delete.
                Ignored if account name is provided.

        Returns:
            True if the account was deleted.
            False if no account was found.
        """
        return AccountManager.delete(filename=filename, name=name, channel=channel)

    @staticmethod
    def save_account(
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        channel: Optional[ChannelType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        proxies: Optional[dict] = None,
        verify: Optional[bool] = None,
        overwrite: Optional[bool] = False,
        set_as_default: Optional[bool] = None,
        private_endpoint: Optional[bool] = False,
        region: Optional[RegionType] = None,
        plans_preference: Optional[PlanType] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Save the account to disk for future use.

        Args:
            token: IBM Cloud API key.
            url: The API URL. Defaults to https://cloud.ibm.com.
            instance: This is an optional parameter to specify the CRN  or service name.
                If set, it will define a default instance for service instantiation,
                if not set, the service will fetch all instances accessible within the account.
            channel: Channel type. ``ibm_cloud`` or ``ibm_quantum_platform``.
            filename: Full path of the file where the account is saved.
            name: Name of the account to save.
            proxies: Proxy configuration. Supported optional keys are
                ``urls`` (a dictionary mapping protocol or protocol and host to the URL of the proxy,
                documented at https://requests.readthedocs.io/en/latest/api/#requests.Session.proxies),
                ``username_ntlm``, ``password_ntlm`` (username and password to enable NTLM user
                authentication)
            verify: Verify the server's TLS certificate.
            overwrite: ``True`` if the existing account is to be overwritten.
            set_as_default: If ``True``, the account is saved in filename,
                as the default account.
            private_endpoint: Connect to private API URL.
            region: Set a region preference. `us-east` or `eu-de`. An instance with this region
                will be prioritized if an instance is not passed in.
            plans_preference: A list of account types, ordered by preference. An instance with the first
                value in the list will be prioritized if an instance is not passed in.
            tags: Set a list of tags to filter available instances. Instances with these tags
                will be prioritized if an instance is not passed in.

        """

        AccountManager.save(
            token=token,
            url=url,
            instance=instance,
            channel=channel,
            filename=filename,
            name=name,
            proxies=ProxyConfiguration(**proxies) if proxies else None,
            verify=verify,
            overwrite=overwrite,
            set_as_default=set_as_default,
            private_endpoint=private_endpoint,
            region=region,
            plans_preference=plans_preference,
            tags=tags,
        )

    @staticmethod
    def saved_accounts(
        default: Optional[bool] = None,
        channel: Optional[ChannelType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
    ) -> dict:
        """List the accounts saved on disk.

        Args:
            default: If set to True, only default accounts are returned.
            channel: Channel type.``ibm_cloud`` or ``ibm_quantum_platform``.
            filename: Name of file whose accounts are returned.
            name: If set, only accounts with the given name are returned.

        Returns:
            A dictionary with information about the accounts saved on disk.

        Raises:
            ValueError: If an invalid account is found on disk.
        """
        return dict(
            map(
                lambda kv: (kv[0], Account.to_saved_format(kv[1])),
                AccountManager.list(
                    default=default, channel=channel, filename=filename, name=name
                ).items(),
            ),
        )

    def backend(
        self,
        name: str,
        instance: Optional[str] = None,
        use_fractional_gates: Optional[bool] = False,
    ) -> Backend:
        """Return a single backend matching the specified filtering.

        Args:
            name: Name of the backend.
            instance: Specify the IBM Cloud account CRN.
            use_fractional_gates: Set True to allow for the backends to include
                fractional gates. Currently this feature cannot be used
                simultaneously with dynamic circuits, PEC, PEA, or gate
                twirling.  When this flag is set, control flow instructions are
                automatically removed from the backend.
                When you use a dynamic circuits feature (e.g. ``if_else``) in your
                algorithm, you must disable this flag to create executable ISA circuits.
                This flag might be modified or removed when our backend
                supports dynamic circuits and fractional gates simultaneously.
                If ``None``, then both fractional gates and control flow operations are
                included in the backends.

        Returns:
            Backend: A backend matching the filtering.

        Raises:
            QiskitBackendNotFoundError: if no backend could be found.
        """
        backends = self.backends(name, instance=instance, use_fractional_gates=use_fractional_gates)
        if not backends:
            cloud_msg_url = ""
            if self._channel in ["ibm_cloud", "ibm_quantum_platform"]:
                cloud_msg_url = (
                    " Learn more about available backends here "
                    "https://quantum.cloud.ibm.com/docs/en/guides/qpu-information#view-your-resources"
                )
            raise QiskitBackendNotFoundError("No backend matches the criteria." + cloud_msg_url)
        return backends[0]

    def _run(
        self,
        program_id: str,
        inputs: Dict,
        options: Optional[Union[RuntimeOptions, Dict]] = None,
        callback: Optional[Callable] = None,
        result_decoder: Optional[Union[Type[ResultDecoder], Sequence[Type[ResultDecoder]]]] = None,
        session_id: Optional[str] = None,
        start_session: Optional[bool] = False,
    ) -> Union[RuntimeJob, RuntimeJobV2]:
        """Execute the runtime program.

        Args:
            program_id: Program ID.
            inputs: Program input parameters. These input values are passed
                to the runtime program.
            options: Runtime options that control the execution environment.

            callback: Callback function to be invoked for any interim results and final result.
                The callback function will receive 2 positional parameters:

                    1. Job ID
                    2. Job result.

            result_decoder: A :class:`ResultDecoder` subclass used to decode job results.
                If more than one decoder is specified, the first is used for interim results and
                the second final results. If not specified, a program-specific decoder or the default
                ``ResultDecoder`` is used.
            session_id: Job ID of the first job in a runtime session.
            start_session: Set to True to explicitly start a runtime session. Defaults to False.

        Returns:
            A ``RuntimeJobV2`` instance representing the execution.

        Raises:
            IBMInputValueError: If input is invalid.
            RuntimeProgramNotFound: If the program cannot be found.
            IBMRuntimeError: An error occurred running the program.
        """

        qrt_options: RuntimeOptions = options
        if options is None:
            qrt_options = RuntimeOptions()
        elif isinstance(options, Dict):
            qrt_options = RuntimeOptions(**options)

        qrt_options.validate(channel=self.channel)

        backend = qrt_options.backend
        if isinstance(backend, str):
            backend = self.backend(name=qrt_options.get_backend_name())

        status = backend.status()
        if status.operational is True and status.status_msg != "active":
            warnings.warn(
                f"The backend {backend.name} currently has a status of {status.status_msg}."
            )

        version = inputs.get("version", 1) if inputs else 1
        try:
            response = self._active_api_client.program_run(
                program_id=program_id,
                backend_name=qrt_options.get_backend_name(),
                params=inputs,
                image=qrt_options.image,
                log_level=qrt_options.log_level,
                session_id=session_id,
                job_tags=qrt_options.job_tags,
                max_execution_time=qrt_options.max_execution_time,
                start_session=start_session,
                session_time=qrt_options.session_time,
                private=qrt_options.private,
            )

        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeProgramNotFound(f"Program not found: {ex.message}") from None
            raise IBMRuntimeError(f"Failed to run program: {ex}") from None

        if response["backend"] and response["backend"] != qrt_options.get_backend_name():
            backend = self.backend(name=response["backend"])

        return RuntimeJobV2(
            backend=backend,
            api_client=self._active_api_client,
            job_id=response["id"],
            program_id=program_id,
            user_callback=callback,
            result_decoder=result_decoder,
            image=qrt_options.image,
            service=self,
            version=version,
            private=qrt_options.private,
        )

    def job(self, job_id: str) -> Union[RuntimeJob, RuntimeJobV2]:
        """Retrieve a runtime job.

        Args:
            job_id: Job ID.

        Returns:
            Runtime job retrieved.

        Raises:
            RuntimeJobNotFound: If the job doesn't exist.
            IBMRuntimeError: If the request failed.
        """
        try:
            response = self._active_api_client.job_get(job_id, exclude_params=False)
        except RequestsApiError as ex:
            if ex.status_code != 404:
                raise IBMRuntimeError(f"Failed to retrieve job: {ex}") from None
            response = None
            for instance, client in self._api_clients.items():
                if instance is not None and instance != self._active_api_client._instance:
                    try:
                        self._active_api_client = client
                        response = self._active_api_client.job_get(job_id, exclude_params=False)
                        break
                    except RequestsApiError:
                        continue
            if response is not None:
                return self._decode_job(response)
            raise RuntimeJobNotFound(f"Job not found: {job_id}") from None

        return self._decode_job(response)

    def jobs(
        self,
        limit: Optional[int] = 10,
        skip: int = 0,
        backend_name: Optional[str] = None,
        pending: bool = None,
        program_id: str = None,
        instance: Optional[str] = None,
        job_tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        descending: bool = True,
    ) -> List[Union[RuntimeJob, RuntimeJobV2]]:
        """Retrieve all runtime jobs, subject to optional filtering.

        Args:
            limit: Number of jobs to retrieve. ``None`` means no limit.
            skip: Starting index for the job retrieval.
            backend_name: Name of the backend to retrieve jobs from.
            pending: Filter by job pending state. If ``True``, 'QUEUED' and 'RUNNING'
                jobs are included. If ``False``, 'DONE', 'CANCELLED' and 'ERROR' jobs
                are included.
            program_id: Filter by Program ID.
            instance: Filter by IBM Cloud instance crn.
            job_tags: Filter by tags assigned to jobs. Matched jobs are associated with all tags.
            session_id: Filter by session id. All jobs in the session will be
                returned in desceding order of the job creation date.
            created_after: Filter by the given start date, in local time. This is used to
                find jobs whose creation dates are after (greater than or equal to) this
                local date/time.
            created_before: Filter by the given end date, in local time. This is used to
                find jobs whose creation dates are before (less than or equal to) this
                local date/time.
            descending: If ``True``, return the jobs in descending order of the job
                creation date (i.e. newest first) until the limit is reached.

        Returns:
            A list of runtime jobs.

        Raises:
            IBMInputValueError: If an input value is invalid.
        """
        if instance and instance != self._active_api_client._instance:
            if instance in self._api_clients:
                self._active_api_client = self._api_clients[instance]
            else:
                new_client = self._create_new_cloud_api_client(instance)
                self._api_clients.update({instance: new_client})
                self._active_api_client = new_client

        if job_tags:
            validate_job_tags(job_tags)

        job_responses = []  # type: List[Dict[str, Any]]
        current_page_limit = limit or 20
        offset = skip
        while True:
            jobs_response = self._active_api_client.jobs_get(
                limit=current_page_limit,
                skip=offset,
                backend_name=backend_name,
                pending=pending,
                program_id=program_id,
                job_tags=job_tags,
                session_id=session_id,
                created_after=created_after,
                created_before=created_before,
                descending=descending,
            )
            job_page = jobs_response["jobs"]
            # count is the total number of jobs that would be returned if
            # there was no limit or skip
            count = jobs_response["count"]

            job_responses += job_page

            if len(job_responses) == count - skip:
                # Stop if there are no more jobs returned by the server.
                break

            if limit:
                if len(job_responses) >= limit:
                    # Stop if we have reached the limit.
                    break
                current_page_limit = limit - len(job_responses)
            else:
                current_page_limit = 20

            offset += len(job_page)

        return [self._decode_job(job) for job in job_responses]

    def delete_job(self, job_id: str) -> None:
        """(DEPRECATED) Delete a runtime job.

        Note that this operation cannot be reversed.

        Args:
            job_id: ID of the job to delete.

        Raises:
            RuntimeJobNotFound: The job doesn't exist.
            IBMRuntimeError: Method is not supported.
        """

        warnings.warn(
            "The delete_job() method is deprecated and will be removed in a future release. "
            "The new IBM Quantum Platform does not support deleting jobs.",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            self._active_api_client.job_delete(job_id)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeJobNotFound(f"Job not found: {ex.message}") from None
            raise IBMRuntimeError(f"Failed to delete job: {ex}") from None

    def usage(self) -> Dict[str, Any]:
        """Return usage information for the current active instance.

        Returns:
            Dict with usage details.
        """
        usage_dict = self._active_api_client.cloud_usage()
        if usage_dict.get("usage_limit_seconds") or usage_dict.get("usage_allocation_seconds"):
            usage_remaining = max(
                usage_dict.get("usage_limit_seconds", usage_dict.get("usage_allocation_seconds"))
                - usage_dict.get("usage_consumed_seconds", 0),
                0,
            )
            usage_dict["usage_remaining_seconds"] = usage_remaining
        return usage_dict

    def _decode_job(self, raw_data: Dict) -> Union[RuntimeJob, RuntimeJobV2]:
        """Decode job data received from the server.

        Args:
            raw_data: Raw job data received from the server.

        Returns:
            Decoded job data.
        """
        instance = self._active_api_client._instance
        # Try to find the right backend
        try:
            if "backend" in raw_data:
                backend = self.backend(raw_data["backend"], instance=instance)
            else:
                backend = None
        except QiskitBackendNotFoundError:
            backend = ibm_backend.IBMRetiredBackend.from_name(
                backend_name=raw_data["backend"],
                api=None,
            )

        version = 2
        params = raw_data.get("params", {})
        if isinstance(params, list):
            if len(params) > 0:
                params = params[0]
            else:
                params = {}
        if not isinstance(params, str):
            if params:
                version = params.get("version", 1)

        if version == 1:
            return RuntimeJob(
                backend=backend,
                api_client=self._active_api_client,
                service=self,
                job_id=raw_data["id"],
                program_id=raw_data.get("program", {}).get("id", ""),
                creation_date=raw_data.get("created", None),
                session_id=raw_data.get("session_id"),
                tags=raw_data.get("tags"),
            )
        return RuntimeJobV2(
            backend=backend,
            api_client=self._active_api_client,
            service=self,
            job_id=raw_data["id"],
            program_id=raw_data.get("program", {}).get("id", ""),
            creation_date=raw_data.get("created", None),
            image=raw_data.get("runtime"),
            session_id=raw_data.get("session_id"),
            tags=raw_data.get("tags"),
            private=raw_data.get("private", False),
        )

    def check_pending_jobs(self) -> None:
        """(DEPRECATED) Check the number of pending jobs and wait for the oldest pending job if
        the maximum number of pending jobs has been reached.
        """

        warnings.warn(
            "The check_pending_jobs() method is deprecated and will be removed in a future release. "
            "The new IBM Quantum Platform does not support this functionality.",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            usage = self.usage().get("byInstance")[0]
            pending_jobs = usage.get("pendingJobs")
            max_pending_jobs = usage.get("maxPendingJobs")
            if pending_jobs >= max_pending_jobs:
                oldest_running = self.jobs(limit=1, descending=False, pending=True)
                if oldest_running:
                    logger.warning(
                        "The pending jobs limit has been reached. "
                        "Waiting for job %s to finish before submitting the next one.",
                        oldest_running[0],
                    )
                    try:
                        oldest_running[0].wait_for_final_state(timeout=300)

                    except Exception as ex:  # pylint: disable=broad-except
                        logger.debug(
                            "An error occurred while waiting for job %s to finish: %s",
                            oldest_running[0].job_id(),
                            ex,
                        )

        except Exception as ex:  # pylint: disable=broad-except
            logger.warning("Unable to retrieve open plan pending jobs details. %s", ex)

    def least_busy(
        self,
        min_num_qubits: Optional[int] = None,
        instance: Optional[str] = None,
        filters: Optional[Callable[["ibm_backend.IBMBackend"], bool]] = None,
        **kwargs: Any,
    ) -> ibm_backend.IBMBackend:
        """Return the least busy available backend.

        Args:
            min_num_qubits: Minimum number of qubits the backend has to have.
            instance: IBM Cloud account CRN.
            filters: Filters can be defined as for the :meth:`backends` method.
                An example to get the operational backends with 5 qubits::

                    QiskitRuntimeService.least_busy(n_qubits=5, operational=True)

        Returns:
            The backend with the fewest number of pending jobs.

        Raises:
            QiskitBackendNotFoundError: If no backend matches the criteria.
        """
        if not self._backends_list:
            self._backends_list = self._active_api_client.list_backends()

        candidates = []
        for backend in self._backends_list:
            if backend["status"]["name"] == "online" and backend["status"]["reason"] == "available":
                candidates.append(backend)

        if filters or kwargs:
            # filters will still be slow because we need the backend configs
            backends = self.backends(
                min_num_qubits=min_num_qubits, filters=filters, instance=instance, **kwargs
            )
            filtered_backend_names = [back.name for back in backends]
            for candidate in candidates.copy():
                if candidate["name"] not in filtered_backend_names:
                    candidates.remove(candidate)

        if min_num_qubits:
            candidates = list(filter(lambda b: b["qubits"] >= min_num_qubits, candidates))
        if not candidates:
            raise QiskitBackendNotFoundError("No backend matches the criteria.")
        sorted_backends = sorted(candidates, key=lambda b: b["queue_length"])
        for back in sorted_backends:
            # We don't know whether or not the backend has a valid config
            try:
                return self.backend(name=back["name"])
            except Exception:  # pylint: disable=broad-except
                pass
        raise QiskitBackendNotFoundError("No backend matches the criteria.")

    def instances(self) -> Sequence[Union[str, Dict[str, str]]]:
        """Return a list that contains a series of dictionaries with the
            following instance identifiers per instance: "crn", "plan", "name".

        Returns:
            A list with instances available for the active account.
        """
        if not self._all_instances:
            self._all_instances = self._account.list_instances()
        return self._all_instances

    def active_instance(self) -> str:
        """Return the crn of the current active instance."""
        return self._active_api_client._instance

    @property
    def channel(self) -> str:
        """Return the channel type used.

        Returns:
            The channel type used.
        """
        return self._channel

    def __repr__(self) -> str:
        return "<{}>".format(self.__class__.__name__)

    def __eq__(self, other: Any) -> bool:
        return (
            self._channel == other._channel
            and self._account.instance == other._account.instance
            and self._account.token == other._account.token
        )
