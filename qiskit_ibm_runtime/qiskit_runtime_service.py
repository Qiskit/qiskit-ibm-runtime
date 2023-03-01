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

import json
import logging
import traceback
import warnings
from datetime import datetime
from collections import OrderedDict
from typing import Dict, Callable, Optional, Union, List, Any, Type, Sequence

from qiskit.providers.backend import BackendV1 as Backend
from qiskit.providers.provider import ProviderV1 as Provider
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends

from qiskit_ibm_runtime import ibm_backend
from .accounts import AccountManager, Account, AccountType, ChannelType
from .proxies import ProxyConfiguration
from .api.clients import AuthClient, VersionClient
from .api.clients.runtime import RuntimeClient
from .api.exceptions import RequestsApiError
from .constants import QISKIT_IBM_RUNTIME_API_URL
from .exceptions import IBMNotAuthorizedError, IBMInputValueError, IBMAccountError
from .exceptions import (
    IBMRuntimeError,
    RuntimeDuplicateProgramError,
    RuntimeProgramNotFound,
    RuntimeJobNotFound,
)
from .hub_group_project import HubGroupProject  # pylint: disable=cyclic-import
from .program.result_decoder import ResultDecoder
from .runtime_job import RuntimeJob
from .runtime_program import RuntimeProgram, ParameterNamespace
from .runtime_session import RuntimeSession  # pylint: disable=cyclic-import
from .utils import RuntimeDecoder, to_base64_string, to_python_identifier
from .utils.backend_decoder import configuration_from_server_data
from .utils.hgp import to_instance_format, from_instance_format
from .api.client_parameters import ClientParameters
from .runtime_options import RuntimeOptions
from .utils.deprecation import (
    deprecate_function,
    issue_deprecation_msg,
    deprecate_arguments,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = "runtime"

DEPRECATED_PROGRAMS = [
    "torch-train",
    "torch-infer",
    "sample-expval",
    "quantum_kernal_alignment",
    "sample-program",
]

_JOB_DEPRECATION_ISSUED = False


class QiskitRuntimeService(Provider):
    """Class for interacting with the Qiskit Runtime service.

    Qiskit Runtime is a new architecture offered by IBM Quantum that
    streamlines computations requiring many iterations. These experiments will
    execute significantly faster within its improved hybrid quantum/classical
    process.

    A sample workflow of using the runtime service::

        from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator, Options
        from qiskit.test.reference_circuits import ReferenceCircuits
        from qiskit.circuit.library import RealAmplitudes
        from qiskit.quantum_info import SparsePauliOp

        # Initialize account.
        service = QiskitRuntimeService()

        # Set options, which can be overwritten at job level.
        options = Options(optimization_level=1)

        # Prepare inputs.
        bell = ReferenceCircuits.bell()
        psi = RealAmplitudes(num_qubits=2, reps=2)
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        theta = [0, 1, 1, 2, 3, 5]

        with Session(service=service, backend="ibmq_qasm_simulator") as session:
            # Submit a request to the Sampler primitive within the session.
            sampler = Sampler(session=session, options=options)
            job = sampler.run(circuits=bell)
            print(f"Sampler results: {job.result()}")

            # Submit a request to the Estimator primitive within the session.
            estimator = Estimator(session=session, options=options)
            job = estimator.run(
                circuits=[psi], observables=[H1], parameter_values=[theta]
            )
            print(f"Estimator results: {job.result()}")
            # Close the session only if all jobs are finished
            # and you don't need to run more in the session.
            session.close()

    The example above uses the dedicated :class:`~qiskit_ibm_runtime.Sampler`
    and :class:`~qiskit_ibm_runtime.Estimator` classes. You can also
    use the :meth:`run` method directly to invoke a Qiskit Runtime program.

    If the program has any interim results, you can use the ``callback``
    parameter of the :meth:`run` method to stream the interim results.
    Alternatively, you can use the :meth:`RuntimeJob.stream_results` method to stream
    the results at a later time, but before the job finishes.

    The :meth:`run` method returns a
    :class:`RuntimeJob` object. You can use its
    methods to perform tasks like checking job status, getting job result, and
    canceling job.
    """

    def __init__(
        self,
        channel: Optional[ChannelType] = None,
        auth: Optional[AccountType] = None,
        token: Optional[str] = None,
        url: Optional[str] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        instance: Optional[str] = None,
        proxies: Optional[dict] = None,
        verify: Optional[bool] = None,
    ) -> None:
        """QiskitRuntimeService constructor

        An account is selected in the following order:

            - Account with the input `name`, if specified.
            - Default account for the `channel` type, if `channel` is specified but `token` is not.
            - Account defined by the input `channel` and `token`, if specified.
            - Account defined by the environment variables, if defined.
            - Default account for the ``ibm_cloud`` account, if one is available.
            - Default account for the ``ibm_quantum`` account, if one is available.

        `instance`, `proxies`, and `verify` can be used to overwrite corresponding
        values in the loaded account.

        Args:
            channel: Channel type. ``ibm_cloud`` or ``ibm_quantum``.
            auth: (DEPRECATED, use `channel` instead) Authentication type. ``cloud`` or ``legacy``.
            token: IBM Cloud API key or IBM Quantum API token.
            url: The API URL.
                Defaults to https://cloud.ibm.com (ibm_cloud) or
                https://auth.quantum-computing.ibm.com/api (ibm_quantum).
            filename: Full path of the file where the account is created.
                Default: _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
            name: Name of the account to load.
            instance: The service instance to use.
                For ``ibm_cloud`` runtime, this is the Cloud Resource Name (CRN) or the service name.
                For ``ibm_quantum`` runtime, this is the hub/group/project in that format.
            proxies: Proxy configuration. Supported optional keys are
                ``urls`` (a dictionary mapping protocol or protocol and host to the URL of the proxy,
                documented at https://docs.python-requests.org/en/latest/api/#requests.Session.proxies),
                ``username_ntlm``, ``password_ntlm`` (username and password to enable NTLM user
                authentication)
            verify: Whether to verify the server's TLS certificate.

        Returns:
            An instance of QiskitRuntimeService.

        Raises:
            IBMInputValueError: If an input is invalid.
        """
        super().__init__()

        if auth:
            self._auth_warning()

        self._account = self._discover_account(
            token=token,
            url=url,
            instance=instance,
            channel=channel,
            auth=auth,
            filename=filename,
            name=name,
            proxies=ProxyConfiguration(**proxies) if proxies else None,
            verify=verify,
        )

        self._client_params = ClientParameters(
            channel=self._account.channel,
            token=self._account.token,
            url=self._account.url,
            instance=self._account.instance,
            proxies=self._account.proxies,
            verify=self._account.verify,
        )

        self._channel = self._account.channel
        self._programs: Dict[str, RuntimeProgram] = {}
        self._backends: Dict[str, "ibm_backend.IBMBackend"] = {}

        if self._channel == "ibm_cloud":
            self._api_client = RuntimeClient(self._client_params)
            # TODO: We can make the backend discovery lazy
            self._backends = self._discover_cloud_backends()
            return
        else:
            auth_client = self._authenticate_ibm_quantum_account(self._client_params)
            # Update client parameters to use authenticated values.
            self._client_params.url = auth_client.current_service_urls()["services"][
                "runtime"
            ]
            self._client_params.token = auth_client.current_access_token()
            self._api_client = RuntimeClient(self._client_params)
            self._hgps = self._initialize_hgps(auth_client)
            for hgp in self._hgps.values():
                for backend_name, backend in hgp.backends.items():
                    if backend_name not in self._backends:
                        self._backends[backend_name] = backend

        # TODO - it'd be nice to allow some kind of autocomplete, but `service.ibmq_foo`
        # just seems wrong since backends are not runtime service instances.
        # self._discover_backends()

    @staticmethod
    def _auth_warning() -> None:
        warnings.warn(
            "Use of `auth` parameter is deprecated and will "
            "be removed in a future release. "
            "You can now use channel='ibm_cloud' or "
            "channel='ibm_quantum' instead.",
            DeprecationWarning,
            stacklevel=3,
        )

    def _discover_account(
        self,
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        channel: Optional[ChannelType] = None,
        auth: Optional[AccountType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = None,
    ) -> Account:
        """Discover account."""
        account = None
        verify_ = verify or True
        if name:
            if filename:
                if any([auth, channel, token, url]):
                    logger.warning(
                        "Loading account from file %s with name %s. Any input 'auth', "
                        "'channel', 'token' or 'url' are ignored.",
                        filename,
                        name,
                    )
            else:
                if any([auth, channel, token, url]):
                    logger.warning(
                        "Loading account with name %s. Any input 'auth', "
                        "'channel', 'token' or 'url' are ignored.",
                        name,
                    )
            account = AccountManager.get(filename=filename, name=name)
        elif auth or channel:
            if auth and auth not in ["legacy", "cloud"]:
                raise ValueError("'auth' can only be 'cloud' or 'legacy'")
            if channel and channel not in ["ibm_cloud", "ibm_quantum"]:
                raise ValueError("'channel' can only be 'ibm_cloud' or 'ibm_quantum'")
            channel = channel or self._get_channel_for_auth(auth=auth)
            if token:
                account = Account(
                    channel=channel,
                    token=token,
                    url=url,
                    instance=instance,
                    proxies=proxies,
                    verify=verify_,
                )
            else:
                if url:
                    logger.warning(
                        "Loading default %s account. Input 'url' is ignored.", channel
                    )
                account = AccountManager.get(
                    filename=filename, name=name, channel=channel
                )
        elif any([token, url]):
            # Let's not infer based on these attributes as they may change in the future.
            raise ValueError(
                "'channel' or 'auth' is required if 'token', or 'url' is specified but 'name' is not."
            )

        if account is None:
            account = AccountManager.get(filename=filename)

        if instance:
            account.instance = instance
        if proxies:
            account.proxies = proxies
        if verify is not None:
            account.verify = verify

        # resolve CRN if needed
        if account.channel == "ibm_cloud":
            self._resolve_crn(account)

        # ensure account is valid, fail early if not
        account.validate()

        return account

    def _discover_cloud_backends(self) -> Dict[str, "ibm_backend.IBMBackend"]:
        """Return the remote backends available for this service instance.

        Returns:
            A dict of the remote backend instances, keyed by backend name.
        """
        ret = OrderedDict()  # type: ignore[var-annotated]
        backends_list = self._api_client.list_backends()
        for backend_name in backends_list:
            raw_config = self._api_client.backend_configuration(
                backend_name=backend_name
            )
            config = configuration_from_server_data(
                raw_config=raw_config, instance=self._account.instance
            )
            if not config:
                continue
            ret[config.backend_name] = ibm_backend.IBMBackend(
                configuration=config,
                service=self,
                api_client=self._api_client,
            )
        return ret

    def _resolve_crn(self, account: Account) -> None:
        account.resolve_crn()

    def _authenticate_ibm_quantum_account(
        self, client_params: ClientParameters
    ) -> AuthClient:
        """Authenticate against IBM Quantum and populate the hub/group/projects.

        Args:
            client_params: Parameters used for server connection.

        Raises:
            IBMInputValueError: If the URL specified is not a valid IBM Quantum authentication URL.
            IBMNotAuthorizedError: If the account is not authorized to use runtime.

        Returns:
            Authentication client.
        """
        version_info = self._check_api_version(client_params)
        # Check the URL is a valid authentication URL.
        if not version_info["new_api"] or "api-auth" not in version_info:
            raise IBMInputValueError(
                "The URL specified ({}) is not an IBM Quantum authentication URL. "
                "Valid authentication URL: {}.".format(
                    client_params.url, QISKIT_IBM_RUNTIME_API_URL
                )
            )
        auth_client = AuthClient(client_params)
        service_urls = auth_client.current_service_urls()
        if not service_urls.get("services", {}).get(SERVICE_NAME):
            raise IBMNotAuthorizedError(
                "This account is not authorized to use ``ibm_quantum`` runtime service."
            )
        return auth_client

    def _initialize_hgps(
        self,
        auth_client: AuthClient,
    ) -> Dict:
        """Authenticate against IBM Quantum and populate the hub/group/projects.

        Args:
            auth_client: Authentication data.

        Raises:
            IBMInputValueError: If the URL specified is not a valid IBM Quantum authentication URL.
            IBMAccountError: If no hub/group/project could be found for this account.

        Returns:
            The hub/group/projects for this account.
        """
        # pylint: disable=unsubscriptable-object
        hgps: OrderedDict[str, HubGroupProject] = OrderedDict()
        service_urls = auth_client.current_service_urls()
        user_hubs = auth_client.user_hubs()
        for hub_info in user_hubs:
            # Build credentials.
            hgp_params = ClientParameters(
                channel=self._account.channel,
                token=auth_client.current_access_token(),
                url=service_urls["http"],
                instance=to_instance_format(
                    hub_info["hub"], hub_info["group"], hub_info["project"]
                ),
                proxies=self._account.proxies,
                verify=self._account.verify,
            )

            # Build the hgp.
            try:
                hgp = HubGroupProject(
                    client_params=hgp_params, instance=hgp_params.instance, service=self
                )
                hgps[hgp.name] = hgp
            except Exception:  # pylint: disable=broad-except
                # Catch-all for errors instantiating the hgp.
                logger.warning(
                    "Unable to instantiate hub/group/project for %s: %s",
                    hub_info,
                    traceback.format_exc(),
                )
        if not hgps:
            raise IBMAccountError(
                "No hub/group/project that supports Qiskit Runtime could "
                "be found for this account."
            )
        # Move open hgp to end of the list
        if len(hgps) > 1:
            open_key, open_val = hgps.popitem(last=False)
            hgps[open_key] = open_val

        default_hgp = self._account.instance
        if default_hgp:
            if default_hgp in hgps:
                # Move user selected hgp to front of the list
                hgps.move_to_end(default_hgp, last=False)
            else:
                warnings.warn(
                    f"Default hub/group/project {default_hgp} not "
                    "found for the account and is ignored."
                )
        return hgps

    @staticmethod
    def _check_api_version(params: ClientParameters) -> Dict[str, Union[bool, str]]:
        """Check the version of the remote server in a set of client parameters.

        Args:
            params: Parameters used for server connection.

        Returns:
            A dictionary with version information.
        """
        version_finder = VersionClient(url=params.url, **params.connection_parameters())
        return version_finder.version()

    def _get_hgp(
        self,
        instance: Optional[str] = None,
        backend_name: Optional[Any] = None,
    ) -> HubGroupProject:
        """Return an instance of `HubGroupProject`.

        This function also allows to find the `HubGroupProject` that contains a backend
        `backend_name`.

        Args:
            instance: The hub/group/project to use.
            backend_name: Name of the IBM Quantum backend.

        Returns:
            An instance of `HubGroupProject` that matches the specified criteria or the default.

        Raises:
            IBMInputValueError: If no hub/group/project matches the specified criteria,
                or if the input value is in an incorrect format.
            QiskitBackendNotFoundError: If backend cannot be found.
        """
        if instance:
            _ = from_instance_format(instance)  # Verify format
            if instance not in self._hgps:
                raise IBMInputValueError(
                    f"Hub/group/project {instance} "
                    "could not be found for this account."
                )
            if backend_name and not self._hgps[instance].backend(backend_name):
                raise QiskitBackendNotFoundError(
                    f"Backend {backend_name} cannot be found in "
                    f"hub/group/project {instance}"
                )
            return self._hgps[instance]

        if not backend_name:
            return list(self._hgps.values())[0]

        for hgp in self._hgps.values():
            if hgp.backend(backend_name):
                return hgp

        error_message = (
            f"Backend {backend_name} cannot be found in any "
            f"hub/group/project for this account."
        )
        if not isinstance(backend_name, str):
            error_message += (
                f" {backend_name} is of type {type(backend_name)} but should "
                f"instead be initialized through the {self}."
            )

        raise QiskitBackendNotFoundError(error_message)

    def _discover_backends(self) -> None:
        """Discovers the remote backends for this account, if not already known."""
        for backend in self._backends.values():
            backend_name = to_python_identifier(backend.name)
            # Append _ if duplicate
            while backend_name in self.__dict__:
                backend_name += "_"
            setattr(self, backend_name, backend)

    # pylint: disable=arguments-differ
    def backends(
        self,
        name: Optional[str] = None,
        min_num_qubits: Optional[int] = None,
        instance: Optional[str] = None,
        filters: Optional[Callable[[List["ibm_backend.IBMBackend"]], bool]] = None,
        **kwargs: Any,
    ) -> List["ibm_backend.IBMBackend"]:
        """Return all backends accessible via this account, subject to optional filtering.

        Args:
            name: Backend name to filter by.
            min_num_qubits: Minimum number of qubits the backend has to have.
            instance: This is only supported for ``ibm_quantum`` runtime and is in the
                hub/group/project format.
            filters: More complex filters, such as lambda functions.
                For example::

                    QiskitRuntimeService.backends(
                        filters=lambda b: b.max_shots > 50000)
                    QiskitRuntimeService.backends(
                        filters=lambda x: ("rz" in x.basis_gates )

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
                <https://qiskit.org/documentation/apidoc/providers_models.html>

        Returns:
            The list of available backends that match the filter.

        Raises:
            IBMInputValueError: If an input is invalid.
        """
        # TODO filter out input_allowed not having runtime
        if self._channel == "ibm_quantum":
            if instance:
                backends = list(self._get_hgp(instance=instance).backends.values())
            else:
                backends = list(self._backends.values())
        else:
            if instance:
                raise IBMInputValueError(
                    "The 'instance' keyword is only supported for ``ibm_quantum`` runtime."
                )
            backends = list(self._backends.values())

        if name:
            kwargs["backend_name"] = name
        if min_num_qubits:
            backends = list(
                filter(lambda b: b.configuration().n_qubits >= min_num_qubits, backends)
            )
        return filter_backends(backends, filters=filters, **kwargs)

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
        auth: Optional[str] = None,
        channel: Optional[ChannelType] = None,
    ) -> bool:
        """Delete a saved account from disk.

        Args:
            filename: Name of file from which to delete the account.
            name: Name of the saved account to delete.
            auth: (DEPRECATED, use `channel` instead) Authentication type of the default
                account to delete. Ignored if account name is provided.
            channel: Channel type of the default account to delete.
                Ignored if account name is provided.

        Returns:
            True if the account was deleted.
            False if no account was found.
        """
        if auth:
            QiskitRuntimeService._auth_warning()
            channel = channel or QiskitRuntimeService._get_channel_for_auth(auth=auth)

        return AccountManager.delete(filename=filename, name=name, channel=channel)

    @staticmethod
    def _get_channel_for_auth(auth: str) -> str:
        """Returns channel type based on auth"""
        if auth == "legacy":
            return "ibm_quantum"
        return "ibm_cloud"

    @staticmethod
    def save_account(
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        channel: Optional[ChannelType] = None,
        auth: Optional[AccountType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        proxies: Optional[dict] = None,
        verify: Optional[bool] = None,
        overwrite: Optional[bool] = False,
    ) -> None:
        """Save the account to disk for future use.

        Args:
            token: IBM Cloud API key or IBM Quantum API token.
            url: The API URL.
                Defaults to https://cloud.ibm.com (ibm_cloud) or
                https://auth.quantum-computing.ibm.com/api (ibm_quantum).
            instance: The CRN (ibm_cloud) or hub/group/project (ibm_quantum).
            channel: Channel type. `ibm_cloud` or `ibm_quantum`.
            auth: (DEPRECATED, use `channel` instead) Authentication type. `cloud` or `legacy`.
            filename: Full path of the file where the account is saved.
            name: Name of the account to save.
            proxies: Proxy configuration. Supported optional keys are
                ``urls`` (a dictionary mapping protocol or protocol and host to the URL of the proxy,
                documented at https://docs.python-requests.org/en/latest/api/#requests.Session.proxies),
                ``username_ntlm``, ``password_ntlm`` (username and password to enable NTLM user
                authentication)
            verify: Verify the server's TLS certificate.
            overwrite: ``True`` if the existing account is to be overwritten.
        """
        if auth:
            QiskitRuntimeService._auth_warning()
            channel = channel or QiskitRuntimeService._get_channel_for_auth(auth)

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
        )

    @staticmethod
    def saved_accounts(
        default: Optional[bool] = None,
        auth: Optional[str] = None,
        channel: Optional[ChannelType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
    ) -> dict:
        """List the accounts saved on disk.

        Args:
            default: If set to True, only default accounts are returned.
            auth: (DEPRECATED, use `channel` instead) If set, only accounts with the given
                authentication type are returned.
            channel: Channel type. `ibm_cloud` or `ibm_quantum`.
            filename: Name of file whose accounts are returned.
            name: If set, only accounts with the given name are returned.

        Returns:
            A dictionary with information about the accounts saved on disk.

        Raises:
            ValueError: If an invalid account is found on disk.
        """
        if auth:
            QiskitRuntimeService._auth_warning()
            channel = channel or QiskitRuntimeService._get_channel_for_auth(auth)
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
        name: str = None,
        instance: Optional[str] = None,
    ) -> Backend:
        """Return a single backend matching the specified filtering.

        Args:
            name: Name of the backend.
            instance: This is only supported for ``ibm_quantum`` runtime and is in the
                hub/group/project format.

        Returns:
            Backend: A backend matching the filtering.

        Raises:
            QiskitBackendNotFoundError: if no backend could be found.
        """
        # pylint: disable=arguments-differ, line-too-long
        backends = self.backends(name, instance=instance)
        if not backends:
            cloud_msg_url = ""
            if self._channel == "ibm_cloud":
                cloud_msg_url = (
                    " Learn more about available backends here "
                    "https://cloud.ibm.com/docs/quantum-computing?topic=quantum-computing-choose-backend "
                )
            raise QiskitBackendNotFoundError(
                "No backend matches the criteria." + cloud_msg_url
            )
        return backends[0]

    def get_backend(self, name: str = None, **kwargs: Any) -> Backend:
        return self.backend(name, **kwargs)

    def pprint_programs(
        self,
        refresh: bool = False,
        detailed: bool = False,
        limit: int = 20,
        skip: int = 0,
    ) -> None:
        """Pretty print information about available runtime programs.

        Args:
            refresh: If ``True``, re-query the server for the programs. Otherwise
                return the cached value.
            detailed: If ``True`` print all details about available runtime programs.
            limit: The number of programs returned at a time. Default and maximum
                value of 20.
            skip: The number of programs to skip.
        """
        programs = self.programs(refresh, limit, skip)
        for prog in programs:
            print("=" * 50)
            if detailed:
                print(str(prog))
            else:
                print(
                    f"{prog.program_id}:",
                )
                print(f"  Name: {prog.name}")
                print(f"  Description: {prog.description}")

    def programs(
        self, refresh: bool = False, limit: int = 20, skip: int = 0
    ) -> List[RuntimeProgram]:
        """Return available runtime programs.

        Currently only program metadata is returned.

        Args:
            refresh: If ``True``, re-query the server for the programs. Otherwise
                return the cached value.
            limit: The number of programs returned at a time. ``None`` means no limit.
            skip: The number of programs to skip.

        Returns:
            A list of runtime programs.
        """
        if skip is None:
            skip = 0
        if not self._programs or refresh:
            self._programs = {}
            current_page_limit = 20
            offset = 0
            while True:
                response = self._api_client.list_programs(
                    limit=current_page_limit, skip=offset
                )
                program_page = response.get("programs", [])
                # count is the total number of programs that would be returned if
                # there was no limit or skip
                count = response.get("count", 0)
                if limit is None:
                    limit = count
                for prog_dict in program_page:
                    program = self._to_program(prog_dict)
                    self._programs[program.program_id] = program
                num_cached_programs = len(self._programs)
                if num_cached_programs == count or num_cached_programs >= (
                    limit + skip
                ):
                    # Stop if there are no more programs returned by the server or
                    # if the number of cached programs is greater than the sum of limit and skip
                    break
                offset += len(program_page)
        if limit is None:
            limit = len(self._programs)
        return list(self._programs.values())[skip : limit + skip]

    def program(self, program_id: str, refresh: bool = False) -> RuntimeProgram:
        """Retrieve a runtime program.

        Currently only program metadata is returned.

        Args:
            program_id: Program ID.
            refresh: If ``True``, re-query the server for the program. Otherwise
                return the cached value.

        Returns:
            Runtime program.

        Raises:
            RuntimeProgramNotFound: If the program does not exist.
            IBMRuntimeError: If the request failed.
        """
        if program_id not in self._programs or refresh:
            try:
                response = self._api_client.program_get(program_id)
            except RequestsApiError as ex:
                if ex.status_code == 404:
                    raise RuntimeProgramNotFound(
                        f"Program not found: {ex.message}"
                    ) from None
                raise IBMRuntimeError(f"Failed to get program: {ex}") from None

            self._programs[program_id] = self._to_program(response)

        return self._programs[program_id]

    def _to_program(self, response: Dict) -> RuntimeProgram:
        """Convert server response to ``RuntimeProgram`` instances.

        Args:
            response: Server response.

        Returns:
            A ``RuntimeProgram`` instance.
        """
        backend_requirements = {}
        parameters = {}
        return_values = {}
        interim_results = {}
        if "spec" in response:
            backend_requirements = response["spec"].get("backend_requirements", {})
            parameters = response["spec"].get("parameters", {})
            return_values = response["spec"].get("return_values", {})
            interim_results = response["spec"].get("interim_results", {})

        return RuntimeProgram(
            program_name=response["name"],
            program_id=response["id"],
            description=response.get("description", ""),
            parameters=parameters,
            return_values=return_values,
            interim_results=interim_results,
            max_execution_time=response.get("cost", 0),
            creation_date=response.get("creation_date", ""),
            update_date=response.get("update_date", ""),
            backend_requirements=backend_requirements,
            is_public=response.get("is_public", False),
            data=response.get("data", ""),
            api_client=self._api_client,
        )

    def run(
        self,
        program_id: str,
        inputs: Union[Dict, ParameterNamespace],
        options: Optional[Union[RuntimeOptions, Dict]] = None,
        callback: Optional[Callable] = None,
        result_decoder: Optional[
            Union[Type[ResultDecoder], Sequence[Type[ResultDecoder]]]
        ] = None,
        instance: Optional[str] = None,
        session_id: Optional[str] = None,
        job_tags: Optional[List[str]] = None,
        max_execution_time: Optional[int] = None,
        start_session: Optional[bool] = False,
    ) -> RuntimeJob:
        """Execute the runtime program.

        Args:
            program_id: Program ID.
            inputs: Program input parameters. These input values are passed
                to the runtime program.
            options: Runtime options that control the execution environment.
                See :class:`RuntimeOptions` for all available options.

            callback: Callback function to be invoked for any interim results and final result.
                The callback function will receive 2 positional parameters:

                    1. Job ID
                    2. Job result.

            result_decoder: A :class:`ResultDecoder` subclass used to decode job results.
                If more than one decoder is specified, the first is used for interim results and
                the second final results. If not specified, a program-specific decoder or the default
                ``ResultDecoder`` is used.
            instance: (DEPRECATED) This is only supported for ``ibm_quantum`` runtime and is in the
                hub/group/project format.
            session_id: Job ID of the first job in a runtime session.
            job_tags: (DEPRECATED) Tags to be assigned to the job. The tags can subsequently be used
                as a filter in the :meth:`jobs()` function call.
            max_execution_time: (DEPRECATED) Maximum execution time in seconds. This overrides
                the max_execution_time of the program.
            start_session: Set to True to explicitly start a runtime session. Defaults to False.

        Returns:
            A ``RuntimeJob`` instance representing the execution.

        Raises:
            IBMInputValueError: If input is invalid.
            RuntimeProgramNotFound: If the program cannot be found.
            IBMRuntimeError: An error occurred running the program.
        """
        if program_id in DEPRECATED_PROGRAMS:
            warnings.warn(
                f"The {program_id} program has been deprecated as of qiskit-ibm-runtime 0.7 \
                and will be removed no sooner than 1 month after the release date.",
                DeprecationWarning,
                stacklevel=2,
            )

        qrt_options: RuntimeOptions = options
        if options is None:
            qrt_options = RuntimeOptions()
        elif isinstance(options, Dict):
            qrt_options = RuntimeOptions(**options)

        deprecated = {
            "instance": instance,
            "job_tags": job_tags,
            "max_execution_time": max_execution_time,
        }
        for name, param in deprecated.items():
            if param is not None:
                deprecate_arguments(
                    deprecated=name,
                    version="0.7",
                    remedy=f'Please specify "{name}" inside "options".',
                )
                setattr(qrt_options, name, param)

        # If using params object, extract as dictionary
        if isinstance(inputs, ParameterNamespace):
            inputs.validate()
            inputs = vars(inputs)

        qrt_options.validate(channel=self.channel)

        backend = None
        hgp_name = None
        if self._channel == "ibm_quantum":
            # Find the right hgp
            hgp = self._get_hgp(
                instance=qrt_options.instance, backend_name=qrt_options.backend
            )
            backend = hgp.backend(qrt_options.backend)
            hgp_name = hgp.name

        try:
            response = self._api_client.program_run(
                program_id=program_id,
                backend_name=qrt_options.backend,
                params=inputs,
                image=qrt_options.image,
                hgp=hgp_name,
                log_level=qrt_options.log_level,
                session_id=session_id,
                job_tags=qrt_options.job_tags,
                max_execution_time=qrt_options.max_execution_time,
                start_session=start_session,
            )
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeProgramNotFound(
                    f"Program not found: {ex.message}"
                ) from None
            raise IBMRuntimeError(f"Failed to run program: {ex}") from None

        if not backend:
            backend = self.backend(name=response["backend"])

        global _JOB_DEPRECATION_ISSUED  # pylint: disable=global-statement
        if not (start_session or session_id) and not _JOB_DEPRECATION_ISSUED:
            # No need to issue warning if session is used since the old style session
            # didn't return a job, and new style returns new job.
            _JOB_DEPRECATION_ISSUED = True
            issue_deprecation_msg(
                msg="Note that the 'job_id' and 'backend' attributes of "
                "a runtime job have been deprecated",
                version="0.7",
                remedy="Please use the job_id() and backend() methods instead.",
            )

        job = RuntimeJob(
            backend=backend,
            api_client=self._api_client,
            client_params=self._client_params,
            job_id=response["id"],
            program_id=program_id,
            params=inputs,
            user_callback=callback,
            result_decoder=result_decoder,
            image=qrt_options.image,
        )
        return job

    @deprecate_function(
        "QiskitRuntimeService.open",
        "0.7",
        "Instead, use the qiskit_ibm_runtime.Session class to create a runtime session.",
    )
    def open(
        self,
        program_id: str,
        inputs: Union[Dict, ParameterNamespace],
        options: Optional[Union[RuntimeOptions, Dict]] = None,
    ) -> RuntimeSession:
        """Open a new runtime session.

        Args:
            program_id: Program ID.
            inputs: Initial program input parameters. These input values are
                persistent throughout the session.
            options: Runtime options that control the execution environment. See
                :class:`RuntimeOptions` for all available options.

        Returns:
            Runtime session.
        """
        return RuntimeSession(
            service=self, program_id=program_id, inputs=inputs, options=options
        )

    def upload_program(
        self, data: str, metadata: Optional[Union[Dict, str]] = None
    ) -> str:
        """Upload a runtime program.

        In addition to program data, the following program metadata is also
        required:

            - name
            - max_execution_time

        Program metadata can be specified using the `metadata` parameter or
        individual parameter (for example, `name` and `description`). If the
        same metadata field is specified in both places, the individual parameter
        takes precedence. For example, if you specify::

            upload_program(metadata={"name": "name1"}, name="name2")

        ``name2`` will be used as the program name.

        Args:
            data: Program data or path of the file containing program data to upload.
            metadata: Name of the program metadata file or metadata dictionary.
                A metadata file needs to be in the JSON format. The ``parameters``,
                ``return_values``, and ``interim_results`` should be defined as JSON Schema.
                See :file:`program/program_metadata_sample.json` for an example. The
                fields in metadata are explained below.

                * name: Name of the program. Required.
                * max_execution_time: Maximum execution time in seconds. Required.
                * description: Program description.
                * is_public: Whether the runtime program should be visible to the public.
                                    The default is ``False``.
                * spec: Specifications for backend characteristics and input parameters
                    required to run the program, interim results and final result.

                    * backend_requirements: Backend requirements.
                    * parameters: Program input parameters in JSON schema format.
                    * return_values: Program return values in JSON schema format.
                    * interim_results: Program interim results in JSON schema format.

        Returns:
            Program ID.

        Raises:
            IBMInputValueError: If required metadata is missing.
            RuntimeDuplicateProgramError: If a program with the same name already exists.
            IBMNotAuthorizedError: If you are not authorized to upload programs.
            IBMRuntimeError: If the upload failed.
        """
        program_metadata = self._read_metadata(metadata=metadata)

        for req in ["name", "max_execution_time"]:
            if req not in program_metadata or not program_metadata[req]:
                raise IBMInputValueError(f"{req} is a required metadata field.")

        if "def main(" not in data:
            # This is the program file
            with open(data, "r", encoding="utf-8") as file:
                data = file.read()

        try:
            program_data = to_base64_string(data)
            response = self._api_client.program_create(
                program_data=program_data, **program_metadata
            )
        except RequestsApiError as ex:
            if ex.status_code == 409:
                raise RuntimeDuplicateProgramError(
                    "Program with the same name already exists."
                ) from None
            if ex.status_code == 403:
                raise IBMNotAuthorizedError(
                    "You are not authorized to upload programs."
                ) from None
            raise IBMRuntimeError(f"Failed to create program: {ex}") from None
        return response["id"]

    def _read_metadata(self, metadata: Optional[Union[Dict, str]] = None) -> Dict:
        """Read metadata.

        Args:
            metadata: Name of the program metadata file or metadata dictionary.

        Returns:
            Return metadata.
        """
        upd_metadata: dict = {}
        if metadata is not None:
            if isinstance(metadata, str):
                with open(metadata, "r", encoding="utf-8") as file:
                    upd_metadata = json.load(file)
            else:
                upd_metadata = metadata
        # TODO validate metadata format
        metadata_keys = [
            "name",
            "max_execution_time",
            "description",
            "spec",
            "is_public",
        ]
        return {key: val for key, val in upd_metadata.items() if key in metadata_keys}

    def update_program(
        self,
        program_id: str,
        data: str = None,
        metadata: Optional[Union[Dict, str]] = None,
        name: str = None,
        description: str = None,
        max_execution_time: int = None,
        spec: Optional[Dict] = None,
    ) -> None:
        """Update a runtime program.

        Program metadata can be specified using the `metadata` parameter or
        individual parameters, such as `name` and `description`. If the
        same metadata field is specified in both places, the individual parameter
        takes precedence.

        Args:
            program_id: Program ID.
            data: Program data or path of the file containing program data to upload.
            metadata: Name of the program metadata file or metadata dictionary.
            name: New program name.
            description: New program description.
            max_execution_time: New maximum execution time.
            spec: New specifications for backend characteristics, input parameters,
                interim results and final result.

        Raises:
            RuntimeProgramNotFound: If the program doesn't exist.
            IBMRuntimeError: If the request failed.
        """
        if not any([data, metadata, name, description, max_execution_time, spec]):
            warnings.warn(
                "None of the 'data', 'metadata', 'name', 'description', "
                "'max_execution_time', or 'spec' parameters is specified. "
                "No update is made."
            )
            return

        if data:
            if "def main(" not in data:
                # This is the program file
                with open(data, "r", encoding="utf-8") as file:
                    data = file.read()
            data = to_base64_string(data)

        if metadata:
            metadata = self._read_metadata(metadata=metadata)
        combined_metadata = self._merge_metadata(
            metadata=metadata,
            name=name,
            description=description,
            max_execution_time=max_execution_time,
            spec=spec,
        )

        try:
            self._api_client.program_update(
                program_id, program_data=data, **combined_metadata
            )
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeProgramNotFound(
                    f"Program not found: {ex.message}"
                ) from None
            raise IBMRuntimeError(f"Failed to update program: {ex}") from None

        if program_id in self._programs:
            program = self._programs[program_id]
            program._refresh()

    def _merge_metadata(self, metadata: Optional[Dict] = None, **kwargs: Any) -> Dict:
        """Merge multiple copies of metadata.
        Args:
            metadata: Program metadata.
            **kwargs: Additional metadata fields to overwrite.
        Returns:
            Merged metadata.
        """
        merged = {}
        metadata = metadata or {}
        metadata_keys = ["name", "max_execution_time", "description", "spec"]
        for key in metadata_keys:
            if kwargs.get(key, None) is not None:
                merged[key] = kwargs[key]
            elif key in metadata.keys():
                merged[key] = metadata[key]
        return merged

    def delete_program(self, program_id: str) -> None:
        """Delete a runtime program.

        Args:
            program_id: Program ID.

        Raises:
            RuntimeProgramNotFound: If the program doesn't exist.
            IBMRuntimeError: If the request failed.
        """
        try:
            self._api_client.program_delete(program_id=program_id)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeProgramNotFound(
                    f"Program not found: {ex.message}"
                ) from None
            raise IBMRuntimeError(f"Failed to delete program: {ex}") from None

        if program_id in self._programs:
            del self._programs[program_id]

    def set_program_visibility(self, program_id: str, public: bool) -> None:
        """Sets a program's visibility.

        Args:
            program_id: Program ID.
            public: If ``True``, make the program visible to all.
                If ``False``, make the program visible to just your account.

        Raises:
            RuntimeProgramNotFound: if program not found (404)
            IBMRuntimeError: if update failed (401, 403)
        """
        try:
            self._api_client.set_program_visibility(program_id, public)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeProgramNotFound(
                    f"Program not found: {ex.message}"
                ) from None
            raise IBMRuntimeError(f"Failed to set program visibility: {ex}") from None

        if program_id in self._programs:
            program = self._programs[program_id]
            program._is_public = public

    def job(self, job_id: str) -> RuntimeJob:
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
            response = self._api_client.job_get(job_id)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeJobNotFound(f"Job not found: {ex.message}") from None
            raise IBMRuntimeError(f"Failed to delete job: {ex}") from None
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
    ) -> List[RuntimeJob]:
        """Retrieve all runtime jobs, subject to optional filtering.

        Args:
            limit: Number of jobs to retrieve. ``None`` means no limit.
            skip: Starting index for the job retrieval.
            backend_name: Name of the backend to retrieve jobs from.
            pending: Filter by job pending state. If ``True``, 'QUEUED' and 'RUNNING'
                jobs are included. If ``False``, 'DONE', 'CANCELLED' and 'ERROR' jobs
                are included.
            program_id: Filter by Program ID.
            instance: This is only supported for ``ibm_quantum`` runtime and is in the
                hub/group/project format.
            job_tags: Filter by tags assigned to jobs. Matched jobs are associated with all tags.
            session_id: Job ID of the first job in a runtime session.
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
        hub = group = project = None
        if instance:
            if self._channel == "ibm_cloud":
                raise IBMInputValueError(
                    "The 'instance' keyword is only supported for ``ibm_quantum`` runtime."
                )
            hub, group, project = from_instance_format(instance)

        job_responses = []  # type: List[Dict[str, Any]]
        current_page_limit = limit or 20
        offset = skip

        while True:
            jobs_response = self._api_client.jobs_get(
                limit=current_page_limit,
                skip=offset,
                backend_name=backend_name,
                pending=pending,
                program_id=program_id,
                hub=hub,
                group=group,
                project=project,
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
        """Delete a runtime job.

        Note that this operation cannot be reversed.

        Args:
            job_id: ID of the job to delete.

        Raises:
            RuntimeJobNotFound: If the job doesn't exist.
            IBMRuntimeError: If the request failed.
        """
        try:
            self._api_client.job_delete(job_id)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeJobNotFound(f"Job not found: {ex.message}") from None
            raise IBMRuntimeError(f"Failed to delete job: {ex}") from None

    def _decode_job(self, raw_data: Dict) -> RuntimeJob:
        """Decode job data received from the server.

        Args:
            raw_data: Raw job data received from the server.

        Returns:
            Decoded job data.
        """
        instance = None
        if self._channel == "ibm_quantum":
            hub = raw_data.get("hub")
            group = raw_data.get("group")
            project = raw_data.get("project")
            if all([hub, group, project]):
                instance = to_instance_format(hub, group, project)
        # Try to find the right backend
        try:
            backend = self.backend(raw_data["backend"], instance=instance)
        except QiskitBackendNotFoundError:
            backend = ibm_backend.IBMRetiredBackend.from_name(
                backend_name=raw_data["backend"],
                api=None,
            )

        params = raw_data.get("params", {})
        if isinstance(params, list):
            if len(params) > 0:
                params = params[0]
            else:
                params = {}
        if not isinstance(params, str):
            params = json.dumps(params)

        decoded = json.loads(params, cls=RuntimeDecoder)
        return RuntimeJob(
            backend=backend,
            api_client=self._api_client,
            client_params=self._client_params,
            job_id=raw_data["id"],
            program_id=raw_data.get("program", {}).get("id", ""),
            params=decoded,
            creation_date=raw_data.get("created", None),
            session_id=raw_data.get("session_id"),
            tags=raw_data.get("tags"),
        )

    def least_busy(
        self,
        min_num_qubits: Optional[int] = None,
        instance: Optional[str] = None,
        filters: Optional[Callable[[List["ibm_backend.IBMBackend"]], bool]] = None,
        **kwargs: Any,
    ) -> ibm_backend.IBMBackend:
        """Return the least busy available backend.

        Args:
            min_num_qubits: Minimum number of qubits the backend has to have.
            instance: This is only supported for ``ibm_quantum`` runtime and is in the
                hub/group/project format.
            filters: Filters can be defined as for the :meth:`backends` method.
                An example to get the operational backends with 5 qubits::

                    QiskitRuntimeService.least_busy(n_qubits=5, operational=True)

        Returns:
            The backend with the fewest number of pending jobs.

        Raises:
            QiskitBackendNotFoundError: If no backend matches the criteria.
        """
        backends = self.backends(
            min_num_qubits=min_num_qubits, instance=instance, filters=filters, **kwargs
        )
        candidates = []
        for back in backends:
            backend_status = back.status()
            if not backend_status.operational or backend_status.status_msg != "active":
                continue
            candidates.append(back)
        if not candidates:
            raise QiskitBackendNotFoundError("No backend matches the criteria.")
        return min(candidates, key=lambda b: b.status().pending_jobs)

    @property
    def auth(self) -> str:
        """Return the authentication type used.

        Returns:
            The authentication type used.
        """
        self._auth_warning()
        return "cloud" if self._channel == "ibm_cloud" else "legacy"

    @property
    def channel(self) -> str:
        """Return the channel type used.

        Returns:
            The channel type used.
        """
        return self._channel

    @property
    def runtime(self):  # type:ignore
        """Return self for compatibility with IBMQ provider.

        Returns:
            self
        """
        return self

    def __repr__(self) -> str:
        return "<{}>".format(self.__class__.__name__)
