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

"""Qiskit runtime service."""

import copy
import json
import logging
import os
import re
import traceback
import warnings
from collections import OrderedDict
from typing import Dict, Callable, Optional, Union, List, Any, Type, Tuple

from qiskit.circuit import QuantumCircuit
from qiskit.providers.backend import BackendV1 as Backend
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends
from qiskit.transpiler import Layout
from typing_extensions import Literal

from qiskit_ibm_runtime import runtime_job, ibm_backend  # pylint: disable=unused-import
from .api.clients import AuthClient, VersionClient
from .api.clients.runtime import RuntimeClient
from .api.exceptions import RequestsApiError
from .backendreservation import BackendReservation
from .credentials import Credentials, HubGroupProjectID, discover_credentials
from .credentials.configrc import (
    remove_credentials,
    read_credentials_from_qiskitrc,
    store_credentials,
)
from .credentials.exceptions import HubGroupProjectIDInvalidStateError
from .constants import QISKIT_IBM_RUNTIME_API_URL
from .exceptions import IBMNotAuthorizedError, IBMInputValueError, IBMProviderError
from .exceptions import (
    QiskitRuntimeError,
    RuntimeDuplicateProgramError,
    RuntimeProgramNotFound,
    RuntimeJobNotFound,
    IBMProviderCredentialsInvalidToken,
    IBMProviderCredentialsInvalidFormat,
    IBMProviderCredentialsNotFound,
    IBMProviderMultipleCredentialsFound,
    IBMProviderCredentialsInvalidUrl,
    IBMProviderValueError,
)
from .hub_group_project import HubGroupProject  # pylint: disable=cyclic-import
from .program.result_decoder import ResultDecoder
from .runner_result import RunnerResult
from .runtime_job import RuntimeJob
from .runtime_program import RuntimeProgram, ParameterNamespace
from .utils import RuntimeDecoder, to_base64_string, to_python_identifier
from .utils.backend import convert_reservation_data

logger = logging.getLogger(__name__)

SERVICE_NAME = "runtime"


class IBMRuntimeService:
    """Class for interacting with the Qiskit Runtime service.

    Qiskit Runtime is a new architecture offered by IBM Quantum that
    streamlines computations requiring many iterations. These experiments will
    execute significantly faster within its improved hybrid quantum/classical
    process.

    The Qiskit Runtime Service allows authorized users to upload their Qiskit
    quantum programs. A Qiskit quantum program, also called a runtime program,
    is a piece of Python code and its metadata that takes certain inputs, performs
    quantum and maybe classical processing, and returns the results. The same or other
    authorized users can invoke these quantum programs by simply passing in parameters.

    A sample workflow of using the runtime service::

        from qiskit import QuantumCircuit
        from qiskit_ibm_runtime import IBMRuntimeService, RunnerResult

        service = IBMRuntimeService()
        backend = service.ibmq_qasm_simulator

        # List all available programs.
        service.pprint_programs()

        # Create a circuit.
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()

        # Set the "circuit-runner" program parameters
        params = service.program(program_id="circuit-runner").parameters()
        params.circuits = qc
        params.measurement_error_mitigation = True

        # Configure backend options
        options = {'backend_name': backend.name()}

        # Execute the circuit using the "circuit-runner" program.
        job = service.run(program_id="circuit-runner",
                          options=options,
                          inputs=params)

        # Get runtime job result.
        result = job.result(decoder=RunnerResult)

    If the program has any interim results, you can use the ``callback``
    parameter of the :meth:`run` method to stream the interim results.
    Alternatively, you can use the :meth:`RuntimeJob.stream_results` method to stream
    the results at a later time, but before the job finishes.

    The :meth:`run` method returns a
    :class:`~qiskit_ibm_runtime.RuntimeJob` object. You can use its
    methods to perform tasks like checking job status, getting job result, and
    canceling job.
    """

    def __init__(
        self,
        auth: Optional[Literal["cloud", "legacy"]] = None,
        token: Optional[str] = None,
        locator: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """IBMRuntimeService constructor

        Args:
            auth: Authentication type. `cloud` or `legacy`. If not specified, the saved default is used.
                If there is no default value, and both accounts were saved on disk, the cloud type is
                used.
            token: Token used for authentication. If not specified, the saved token is used.
            locator: The authentication url, if `auth=legacy`. Otherwise the CRN.
            **kwargs: Additional settings for the connection:

                * proxies (dict): proxy configuration.
                * verify (bool): verify the server's TLS certificate.

        Returns:
            An instance of IBMRuntimeService.

        Raises:
            IBMProviderCredentialsInvalidFormat: If the default hub/group/project saved on
                disk could not be parsed.
            IBMProviderCredentialsNotFound: If no IBM Quantum credentials can be found.
            IBMProviderCredentialsInvalidUrl: If the URL specified is not
                a valid IBM Quantum authentication URL.
            IBMProviderCredentialsInvalidToken: If the `token` is not a valid IBM Quantum token.
        """
        super().__init__()
        if auth == "cloud":
            raise IBMProviderCredentialsNotFound(
                "Support for auth type 'cloud' has not yet been implemented."
            )

        account_credentials, account_preferences = self._resolve_credentials(
            token=token, url=locator, **kwargs
        )
        self._initialize_hgps(
            credentials=account_credentials, preferences=account_preferences
        )
        self._backends: Dict[str, "ibm_backend.IBMBackend"] = {}
        self._api_client = None
        self._programs_first_call = True
        hgps = self._get_hgps()
        for hgp in hgps:
            for name, backend in hgp.backends.items():
                if name not in self._backends:
                    self._backends[name] = backend
            if not self._api_client and hgp.has_service("runtime"):
                self._default_hgp = hgp
                self._api_client = RuntimeClient(self._default_hgp.credentials)
                self._access_token = self._default_hgp.credentials.access_token
                self._ws_url = self._default_hgp.credentials.runtime_url.replace(
                    "https", "wss"
                )
                self._programs: Dict[str, RuntimeProgram] = {}
        self._discover_backends()

    def _resolve_credentials(
        self, token: Optional[str] = None, url: Optional[str] = None, **kwargs: Any
    ) -> Tuple[Credentials, Dict]:
        """Resolve credentials after looking up env variables and credentials saved on disk

        Args:
            token: IBM Quantum token.
            url: URL for the IBM Quantum authentication server.
            **kwargs: Additional settings for the connection:

                * proxies (dict): proxy configuration.
                * verify (bool): verify the server's TLS certificate.

        Returns:
            Tuple of account_credentials, preferences

        Raises:
            IBMProviderCredentialsInvalidFormat: If the default hub/group/project saved on
                disk could not be parsed.
            IBMProviderCredentialsNotFound: If no IBM Quantum credentials can be found.
            IBMProviderCredentialsInvalidToken: If the `token` is not a valid IBM Quantum token.
            IBMProviderMultipleCredentialsFound: If multiple IBM Quantum credentials are found.
        """
        if token:
            if not isinstance(token, str):
                raise IBMProviderCredentialsInvalidToken(
                    "Invalid IBM Quantum token "
                    'found: "{}" of type {}.'.format(token, type(token))
                )
            url = (
                url
                or os.getenv("QISKIT_IBM_RUNTIME_API_URL")
                or QISKIT_IBM_RUNTIME_API_URL
            )
            account_credentials = Credentials(
                token=token, url=url, auth_url=url, **kwargs
            )
            preferences: Optional[Dict] = {}
        else:
            # Check for valid credentials in env variables or qiskitrc file.
            try:
                saved_credentials, preferences = discover_credentials()
            except HubGroupProjectIDInvalidStateError as ex:
                raise IBMProviderCredentialsInvalidFormat(
                    "Invalid hub/group/project data found {}".format(str(ex))
                ) from ex
            credentials_list = list(saved_credentials.values())
            if not credentials_list:
                raise IBMProviderCredentialsNotFound(
                    "No IBM Quantum credentials found."
                )
            if len(credentials_list) > 1:
                raise IBMProviderMultipleCredentialsFound(
                    "Multiple IBM Quantum Experience credentials found."
                )
            account_credentials = credentials_list[0]
        return account_credentials, preferences

    def _initialize_hgps(
        self, credentials: Credentials, preferences: Optional[Dict] = None
    ) -> None:
        """Authenticate against IBM Quantum and populate the hub/group/projects.

        Args:
            credentials: Credentials for IBM Quantum.
            preferences: Account preferences.

        Raises:
            IBMProviderCredentialsInvalidUrl: If the URL specified is not
                a valid IBM Quantum authentication URL.
            IBMProviderError: If no hub/group/project could be found for this account.
        """
        self._hgps: Dict[HubGroupProjectID, HubGroupProject] = OrderedDict()
        version_info = self._check_api_version(credentials)
        # Check the URL is a valid authentication URL.
        if not version_info["new_api"] or "api-auth" not in version_info:
            raise IBMProviderCredentialsInvalidUrl(
                "The URL specified ({}) is not an IBM Quantum authentication URL. "
                "Valid authentication URL: {}.".format(
                    credentials.url, QISKIT_IBM_RUNTIME_API_URL
                )
            )
        auth_client = AuthClient(
            credentials.token,
            credentials.base_url,
            **credentials.connection_parameters(),
        )
        service_urls = auth_client.current_service_urls()
        user_hubs = auth_client.user_hubs()
        preferences = preferences or {}
        is_open = True  # First hgp is open access
        for hub_info in user_hubs:
            # Build credentials.
            hgp_credentials = Credentials(
                credentials.token,
                access_token=auth_client.current_access_token(),
                url=service_urls["http"],
                auth_url=credentials.auth_url,
                websockets_url=service_urls["ws"],
                proxies=credentials.proxies,
                verify=credentials.verify,
                services=service_urls.get("services", {}),
                default_provider=credentials.default_provider,
                **hub_info,
            )
            hgp_credentials.preferences = preferences.get(
                hgp_credentials.unique_id(), {}
            )
            # Build the hgp.
            try:
                hgp = HubGroupProject(
                    credentials=hgp_credentials, service=self, is_open=is_open
                )
                self._hgps[hgp.credentials.unique_id()] = hgp
                is_open = False  # hgps after first are premium and not open access
            except Exception:  # pylint: disable=broad-except
                # Catch-all for errors instantiating the hgp.
                logger.warning(
                    "Unable to instantiate hub/group/project for %s: %s",
                    hub_info,
                    traceback.format_exc(),
                )
        if not self._hgps:
            raise IBMProviderError(
                "No hub/group/project could be found for this account."
            )
        # Move open hgp to end of the list
        if len(self._hgps) > 1:
            open_hgp = self._get_hgp()
            self._hgps.move_to_end(open_hgp.credentials.unique_id())
        if credentials.default_provider:
            # Move user selected hgp to front of the list
            hub, group, project = credentials.default_provider.to_tuple()
            default_hgp = self._get_hgp(hub=hub, group=group, project=project)
            self._hgps.move_to_end(default_hgp.credentials.unique_id(), last=False)

    @staticmethod
    def _check_api_version(credentials: Credentials) -> Dict[str, Union[bool, str]]:
        """Check the version of the remote server in a set of credentials.

        Args:
            credentials: IBM Quantum Credentials

        Returns:
            A dictionary with version information.
        """
        version_finder = VersionClient(
            credentials.base_url, **credentials.connection_parameters()
        )
        return version_finder.version()

    def _get_hgp(
        self,
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
        backend_name: Optional[str] = None,
        service_name: Optional[str] = None,
    ) -> HubGroupProject:
        """Return an instance of `HubGroupProject` for a single hub/group/project combination.

        This function also allows to find the `HubGroupProject` that contains a backend
        `backend_name` providing service `service_name`.

        Args:
            hub: Name of the hub.
            group: Name of the group.
            project: Name of the project.
            backend_name: Name of the IBM Quantum backend.
            service_name: Name of the IBM Quantum service.

        Returns:
            An instance of `HubGroupProject` that matches the specified criteria or the default.

        Raises:
            IBMProviderError: If no hub/group/project matches the specified criteria,
                if more than one hub/group/project matches the specified criteria, if
                no hub/group/project could be found for this account or if no backend matches the
                criteria.
        """
        # If any `hub`, `group`, or `project` is specified, make sure all parameters are set.
        if any([hub, group, project]) and not all([hub, group, project]):
            raise IBMProviderError(
                "The hub, group, and project parameters must all be "
                "specified. "
                'hub = "{}", group = "{}", project = "{}"'.format(hub, group, project)
            )
        hgps = self._get_hgps(hub=hub, group=group, project=project)
        if any([hub, group, project]):
            if not hgps:
                raise IBMProviderError(
                    "No hub/group/project matches the specified criteria: "
                    "hub = {}, group = {}, project = {}".format(hub, group, project)
                )
            if len(hgps) > 1:
                raise IBMProviderError(
                    "More than one hub/group/project matches the "
                    "specified criteria. hub = {}, group = {}, project = {}".format(
                        hub, group, project
                    )
                )
        elif not hgps:
            # Prevent edge case where no hub/group/project is available.
            raise IBMProviderError(
                "No hub/group/project could be found for this account."
            )
        elif backend_name and service_name:
            for hgp in hgps:
                if hgp.has_service(service_name) and hgp.get_backend(backend_name):
                    return hgp
            raise IBMProviderError("No backend matches the criteria.")
        return hgps[0]

    def _get_hgps(
        self,
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
    ) -> List[HubGroupProject]:
        """Return a list of `HubGroupProject` instances, subject to optional filtering.

        Args:
            hub: Name of the hub.
            group: Name of the group.
            project: Name of the project.

        Returns:
            A list of `HubGroupProject` instances that match the specified criteria.
        """
        filters: List[Callable[[HubGroupProjectID], bool]] = []
        if hub:
            filters.append(lambda hgp: hgp.hub == hub)
        if group:
            filters.append(lambda hgp: hgp.group == group)
        if project:
            filters.append(lambda hgp: hgp.project == project)
        hgps = [hgp for key, hgp in self._hgps.items() if all(f(key) for f in filters)]
        return hgps

    def _discover_backends(self) -> None:
        """Discovers the remote backends for this account, if not already known."""
        for backend in self._backends.values():
            backend_name = to_python_identifier(backend.name())
            # Append _ if duplicate
            while backend_name in self.__dict__:
                backend_name += "_"
            setattr(self, backend_name, backend)

    def backends(
        self,
        name: Optional[str] = None,
        filters: Optional[Callable[[List["ibm_backend.IBMBackend"]], bool]] = None,
        min_num_qubits: Optional[int] = None,
        input_allowed: Optional[Union[str, List[str]]] = None,
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
        **kwargs: Any,
    ) -> List["ibm_backend.IBMBackend"]:
        """Return all backends accessible via this account, subject to optional filtering.

        Args:
            name: Backend name to filter by.
            filters: More complex filters, such as lambda functions.
                For example::

                    IBMRuntimeService.backends(
                        filters=lambda b: b.configuration().quantum_volume > 16)
            min_num_qubits: Minimum number of qubits the backend has to have.
            input_allowed: Filter by the types of input the backend supports.
                Valid input types are ``job`` (circuit job) and ``runtime`` (Qiskit Runtime).
                For example, ``inputs_allowed='runtime'`` will return all backends
                that support Qiskit Runtime. If a list is given, the backend must
                support all types specified in the list.
            hub: Name of the hub.
            group: Name of the group.
            project: Name of the project.
            kwargs: Simple filters that specify a ``True``/``False`` criteria in the
                backend configuration, backends status, or provider credentials.
                An example to get the operational backends with 5 qubits::

                    IBMRuntimeService.backends(n_qubits=5, operational=True)

        Returns:
            The list of available backends that match the filter.

        Raises:
            IBMBackendValueError: If only one or two parameters from `hub`, `group`,
                `project` are specified.
        """
        backends: List["ibm_backend.IBMBackend"] = list()
        if all([hub, group, project]):
            hgp = self._get_hgp(hub, group, project)
            backends = list(hgp.backends.values())
        else:
            backends = list(self._backends.values())
        # Special handling of the `name` parameter, to support alias resolution.
        if name:
            aliases = self._aliased_backend_names()
            aliases.update(self._deprecated_backend_names())
            name = aliases.get(name, name)
            kwargs["backend_name"] = name
        if min_num_qubits:
            backends = list(
                filter(lambda b: b.configuration().n_qubits >= min_num_qubits, backends)
            )
        if input_allowed:
            if not isinstance(input_allowed, list):
                input_allowed = [input_allowed]
            backends = list(
                filter(
                    lambda b: set(input_allowed)
                    <= set(b.configuration().input_allowed),
                    backends,
                )
            )
        return filter_backends(backends, filters=filters, **kwargs)

    def my_reservations(self) -> List[BackendReservation]:
        """Return your upcoming reservations.

        Returns:
            A list of your upcoming reservations.
        """
        raw_response = self._default_hgp._api_client.my_reservations()
        return convert_reservation_data(raw_response)

    @staticmethod
    def _deprecated_backend_names() -> Dict[str, str]:
        """Returns deprecated backend names."""
        return {
            "ibmqx_qasm_simulator": "ibmq_qasm_simulator",
            "ibmqx_hpc_qasm_simulator": "ibmq_qasm_simulator",
            "real": "ibmqx1",
        }

    @staticmethod
    def _aliased_backend_names() -> Dict[str, str]:
        """Returns aliased backend names."""
        return {
            "ibmq_5_yorktown": "ibmqx2",
            "ibmq_5_tenerife": "ibmqx4",
            "ibmq_16_rueschlikon": "ibmqx5",
            "ibmq_20_austin": "QS1_1",
        }

    def active_account(self) -> Optional[Dict[str, str]]:
        """Return the IBM Quantum account currently in use for the session.

        Returns:
            A dictionary with information about the account currently in the session,
                None if there is no active account in session
        """
        if not self._hgps:
            return None
        first_hgp = self._get_hgp()
        return {
            "token": first_hgp.credentials.token,
            "url": first_hgp.credentials.auth_url,
        }

    @staticmethod
    def delete_account() -> None:
        """Delete the saved account from disk.

        Raises:
            IBMProviderCredentialsNotFound: If no valid IBM Quantum
                credentials can be found on disk.
            IBMProviderCredentialsInvalidUrl: If invalid IBM Quantum
                credentials are found on disk.
        """
        stored_credentials, _ = read_credentials_from_qiskitrc()
        if not stored_credentials:
            raise IBMProviderCredentialsNotFound(
                "No IBM Quantum credentials found on disk."
            )
        credentials = list(stored_credentials.values())[0]
        if credentials.url != QISKIT_IBM_RUNTIME_API_URL:
            raise IBMProviderCredentialsInvalidUrl(
                "Invalid IBM Quantum credentials found on disk. "
            )
        remove_credentials(credentials)

    @staticmethod
    def save_account(
        token: str,
        url: str = QISKIT_IBM_RUNTIME_API_URL,
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> None:
        """Save the account to disk for future use.

        Note:
            If storing a default hub/group/project to disk, all three parameters
            `hub`, `group`, `project` must be specified.

        Args:
            token: IBM Quantum token.
            url: URL for the IBM Quantum authentication server.
            hub: Name of the hub.
            group: Name of the group.
            project: Name of the project.
            overwrite: Overwrite existing credentials.
            **kwargs:
                * proxies (dict): Proxy configuration for the server.
                * verify (bool): If False, ignores SSL certificates errors

        Raises:
            IBMProviderCredentialsInvalidUrl: If the `url` is not a valid
                IBM Quantum authentication URL.
            IBMProviderCredentialsInvalidToken: If the `token` is not a valid
                IBM Quantum token.
            IBMProviderValueError: If only one or two parameters from `hub`, `group`,
                `project` are specified.
        """
        if url != QISKIT_IBM_RUNTIME_API_URL:
            raise IBMProviderCredentialsInvalidUrl(
                "Invalid IBM Quantum credentials found."
            )
        if not token or not isinstance(token, str):
            raise IBMProviderCredentialsInvalidToken(
                "Invalid IBM Quantum token "
                'found: "{}" of type {}.'.format(token, type(token))
            )
        # If any `hub`, `group`, or `project` is specified, make sure all parameters are set.
        if any([hub, group, project]) and not all([hub, group, project]):
            raise IBMProviderValueError(
                "The hub, group, and project parameters must all be "
                "specified when storing a default hub/group/project to "
                'disk: hub = "{}", group = "{}", project = "{}"'.format(
                    hub, group, project
                )
            )
        # If specified, get the hub/group/project to store.
        default_hgp_id = (
            HubGroupProjectID(hub, group, project)
            if all([hub, group, project])
            else None
        )
        credentials = Credentials(
            token=token, url=url, default_provider=default_hgp_id, **kwargs
        )
        store_credentials(credentials, overwrite=overwrite)

    @staticmethod
    def saved_account() -> Dict[str, str]:
        """List the account saved on disk.

        Returns:
            A dictionary with information about the account saved on disk.

        Raises:
            IBMProviderCredentialsInvalidUrl: If invalid IBM Quantum
                credentials are found on disk.
        """
        stored_credentials, _ = read_credentials_from_qiskitrc()
        if not stored_credentials:
            return {}
        credentials = list(stored_credentials.values())[0]
        if credentials.url != QISKIT_IBM_RUNTIME_API_URL:
            raise IBMProviderCredentialsInvalidUrl(
                "Invalid IBM Quantum credentials found on disk."
            )
        return {"token": credentials.token, "url": credentials.url}

    def get_backend(
        self,
        name: str = None,
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
        **kwargs: Any,
    ) -> Backend:
        """Return a single backend matching the specified filtering.

        Args:
            name (str): name of the backend.
            hub: Name of the hub.
            group: Name of the group.
            project: Name of the project.
            **kwargs: dict used for filtering.

        Returns:
            Backend: a backend matching the filtering.

        Raises:
            QiskitBackendNotFoundError: if no backend could be found or
                more than one backend matches the filtering criteria.
            IBMProviderValueError: If only one or two parameters from `hub`, `group`,
                `project` are specified.
        """
        # pylint: disable=arguments-differ
        backends = self.backends(name, hub=hub, group=group, project=project, **kwargs)
        if len(backends) > 1:
            raise QiskitBackendNotFoundError(
                "More than one backend matches the criteria"
            )
        if not backends:
            raise QiskitBackendNotFoundError("No backend matches the criteria")
        return backends[0]

    def run_circuits(
        self,
        circuits: Union[QuantumCircuit, List[QuantumCircuit]],
        backend_name: str,
        shots: Optional[int] = None,
        initial_layout: Optional[Union[Layout, Dict, List]] = None,
        layout_method: Optional[str] = None,
        routing_method: Optional[str] = None,
        translation_method: Optional[str] = None,
        seed_transpiler: Optional[int] = None,
        optimization_level: int = 1,
        init_qubits: bool = True,
        rep_delay: Optional[float] = None,
        transpiler_options: Optional[dict] = None,
        measurement_error_mitigation: bool = False,
        use_measure_esp: Optional[bool] = None,
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
        **run_config: Dict,
    ) -> "runtime_job.RuntimeJob":
        """Execute the input circuit(s) on a backend using the runtime service.

        Note:
            This method uses the IBM Quantum runtime service which is not
            available to all accounts.

        Args:
            circuits: Circuit(s) to execute.

            backend_name: Name of the backend to execute circuits on.
                Transpiler options are automatically grabbed from backend configuration
                and properties unless otherwise specified.

            shots: Number of repetitions of each circuit, for sampling. If not specified,
                the backend default is used.

            initial_layout: Initial position of virtual qubits on physical qubits.

            layout_method: Name of layout selection pass ('trivial', 'dense',
                'noise_adaptive', 'sabre').
                Sometimes a perfect layout can be available in which case the layout_method
                may not run.

            routing_method: Name of routing pass ('basic', 'lookahead', 'stochastic', 'sabre')

            translation_method: Name of translation pass ('unroller', 'translator', 'synthesis')

            seed_transpiler: Sets random seed for the stochastic parts of the transpiler.

            optimization_level: How much optimization to perform on the circuits.
                Higher levels generate more optimized circuits, at the expense of longer
                transpilation time.
                If None, level 1 will be chosen as default.

            init_qubits: Whether to reset the qubits to the ground state for each shot.

            rep_delay: Delay between programs in seconds. Only supported on certain
                backends (``backend.configuration().dynamic_reprate_enabled`` ). If supported,
                ``rep_delay`` will be used instead of ``rep_time`` and must be from the
                range supplied by the backend (``backend.configuration().rep_delay_range``).
                Default is given by ``backend.configuration().default_rep_delay``.

            transpiler_options: Additional transpiler options.

            measurement_error_mitigation: Whether to apply measurement error mitigation.

            use_measure_esp: Whether to use excited state promoted (ESP) readout for measurements
                which are the final instruction on a qubit. ESP readout can offer higher fidelity
                than standard measurement sequences. See
                `here <https://arxiv.org/pdf/2008.08571.pdf>`_.

            hub: Name of the hub.

            group: Name of the group.

            project: Name of the project.

            **run_config: Extra arguments used to configure the circuit execution.

        Returns:
            Runtime job.
        """
        inputs = copy.deepcopy(run_config)  # type: Dict[str, Any]
        inputs["circuits"] = circuits
        inputs["optimization_level"] = optimization_level
        inputs["init_qubits"] = init_qubits
        inputs["measurement_error_mitigation"] = measurement_error_mitigation
        if shots:
            inputs["shots"] = shots
        if initial_layout:
            inputs["initial_layout"] = initial_layout
        if layout_method:
            inputs["layout_method"] = layout_method
        if routing_method:
            inputs["routing_method"] = routing_method
        if translation_method:
            inputs["translation_method"] = translation_method
        if seed_transpiler:
            inputs["seed_transpiler"] = seed_transpiler
        if rep_delay:
            inputs["rep_delay"] = rep_delay
        if transpiler_options:
            inputs["transpiler_options"] = transpiler_options
        if use_measure_esp is not None:
            inputs["use_measure_esp"] = use_measure_esp
        options = {"backend_name": backend_name}
        return self.run(
            "circuit-runner",
            options=options,
            inputs=inputs,
            result_decoder=RunnerResult,
            hub=hub,
            group=group,
            project=project,
        )

    def pprint_programs(
        self,
        refresh: bool = False,
        detailed: bool = False,
        search: Optional[str] = "",
        limit: int = 20,
        skip: int = 0,
    ) -> None:
        """Pretty print information about available runtime programs.

        Args:
            refresh: If ``True``, re-query the server for the programs. Otherwise
                return the cached value.
            detailed: If ``True`` print all details about available runtime programs.
            search: Returns programs containing search word in name or description.
            limit: The number of programs returned at a time. Default and maximum
                value of 20.
            skip: The number of programs to skip.
        """
        programs = self.programs(refresh, search, limit, skip)
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
        self,
        refresh: bool = False,
        search: Optional[str] = "",
        limit: int = 20,
        skip: int = 0,
    ) -> List[RuntimeProgram]:
        """Return available runtime programs.

        Currently only program metadata is returned.

        Args:
            refresh: If ``True``, re-query the server for the programs. Otherwise
                return the cached value.
            search: Returns programs containing search word in name or description.
            limit: The number of programs returned at a time. ``None`` means no limit.
            skip: The number of programs to skip.

        Returns:
            A list of runtime programs.
        """
        refreshed = False
        if skip is None:
            skip = 0
        if not self._programs or refresh:
            self._programs = {}
            current_page_limit = 20
            offset = 0
            program_search = "" if self._programs_first_call else search
            while True:
                response = self._api_client.list_programs(
                    search=program_search, limit=current_page_limit, skip=offset
                )
                program_page = response.get("programs", [])
                # count is the total number of programs that would be returned if
                # there was no limit or skip
                count = response.get("count", 0)
                for prog_dict in program_page:
                    program = self._to_program(prog_dict)
                    self._programs[program.program_id] = program
                if len(self._programs) == count:
                    if not self._programs_first_call:
                        refreshed = True
                    self._programs_first_call = False
                    # Stop if there are no more programs returned by the server.
                    break
                offset += len(program_page)
        if limit is None:
            limit = len(self._programs)
        if search:
            if refreshed:
                return list(self._programs.values())[skip : limit + skip]
            matched_programs = []
            for program in list(self._programs.values()):
                if search in program.name or search in program.description:
                    matched_programs.append(program)
            return matched_programs[skip : limit + skip]
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
            QiskitRuntimeError: If the request failed.
        """
        if program_id not in self._programs or refresh:
            try:
                response = self._api_client.program_get(program_id)
            except RequestsApiError as ex:
                if ex.status_code == 404:
                    raise RuntimeProgramNotFound(
                        f"Program not found: {ex.message}"
                    ) from None
                raise QiskitRuntimeError(f"Failed to get program: {ex}") from None

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
        options: Dict,
        inputs: Union[Dict, ParameterNamespace],
        callback: Optional[Callable] = None,
        result_decoder: Optional[Type[ResultDecoder]] = None,
        image: Optional[str] = "",
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
    ) -> RuntimeJob:
        """Execute the runtime program.

        Args:
            program_id: Program ID.
            options: Runtime options that control the execution environment.
                Currently the only available option is ``backend_name``, which is required.
            inputs: Program input parameters. These input values are passed
                to the runtime program.
            callback: Callback function to be invoked for any interim results.
                The callback function will receive 2 positional parameters:

                    1. Job ID
                    2. Job interim result.

            result_decoder: A :class:`ResultDecoder` subclass used to decode job results.
                ``ResultDecoder`` is used if not specified.
            image: The runtime image used to execute the program, specified in the form
                of image_name:tag. Not all accounts are authorized to select a different image.
            hub: Name of the hub.
            group: Name of the group.
            project: Name of the project.

        Returns:
            A ``RuntimeJob`` instance representing the execution.

        Raises:
            IBMInputValueError: If input is invalid.
        """
        if "backend_name" not in options:
            raise IBMInputValueError('"backend_name" is required field in "options"')
        # If using params object, extract as dictionary
        if isinstance(inputs, ParameterNamespace):
            inputs.validate()
            inputs = vars(inputs)

        if image and not re.match(
            "[a-zA-Z0-9]+([/.\\-_][a-zA-Z0-9]+)*:[a-zA-Z0-9]+([.\\-_][a-zA-Z0-9]+)*$",
            image,
        ):
            raise IBMInputValueError('"image" needs to be in form of image_name:tag')
        backend_name = options["backend_name"]
        if not all([hub, group, project]) and self._default_hgp.get_backend(
            backend_name
        ):
            hgp = self._default_hgp
        else:
            hgp = self._get_hgp(
                hub=hub,
                group=group,
                project=project,
                backend_name=backend_name,
                service_name=SERVICE_NAME,
            )
        credentials = hgp.credentials
        api_client = (
            self._api_client if hgp == self._default_hgp else RuntimeClient(credentials)
        )
        result_decoder = result_decoder or ResultDecoder
        response = api_client.program_run(
            program_id=program_id,
            credentials=credentials,
            backend_name=backend_name,
            params=inputs,
            image=image,
        )

        backend = self.get_backend(backend_name)
        job = RuntimeJob(
            backend=backend,
            api_client=api_client,
            credentials=credentials,
            job_id=response["id"],
            program_id=program_id,
            params=inputs,
            user_callback=callback,
            result_decoder=result_decoder,
            image=image,
        )
        return job

    def upload_program(
        self, data: str, metadata: Optional[Union[Dict, str]] = None
    ) -> str:
        """Upload a runtime program.

        In addition to program data, the following program metadata is also
        required:

            - name
            - max_execution_time
            - description

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
                * description: Program description. Required.
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
            QiskitRuntimeError: If the upload failed.
        """
        program_metadata = self._read_metadata(metadata=metadata)

        for req in ["name", "description", "max_execution_time"]:
            if req not in program_metadata or not program_metadata[req]:
                raise IBMInputValueError(f"{req} is a required metadata field.")

        if "def main(" not in data:
            # This is the program file
            with open(data, "r") as file:
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
            raise QiskitRuntimeError(f"Failed to create program: {ex}") from None
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
                with open(metadata, "r") as file:
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
            QiskitRuntimeError: If the request failed.
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
                with open(data, "r") as file:
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
            raise QiskitRuntimeError(f"Failed to update program: {ex}") from None

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
            QiskitRuntimeError: If the request failed.
        """
        try:
            self._api_client.program_delete(program_id=program_id)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeProgramNotFound(
                    f"Program not found: {ex.message}"
                ) from None
            raise QiskitRuntimeError(f"Failed to delete program: {ex}") from None

        if program_id in self._programs:
            del self._programs[program_id]

    def set_program_visibility(self, program_id: str, public: bool) -> None:
        """Sets a program's visibility.

        Args:
            program_id: Program ID.
            public: If ``True``, make the program visible to all.
                If ``False``, make the program visible to just your account.

        Raises:
            RuntimeJobNotFound: if program not found (404)
            QiskitRuntimeError: if update failed (401, 403)
        """
        try:
            self._api_client.set_program_visibility(program_id, public)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeJobNotFound(f"Program not found: {ex.message}") from None
            raise QiskitRuntimeError(
                f"Failed to set program visibility: {ex}"
            ) from None

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
            QiskitRuntimeError: If the request failed.
        """
        try:
            response = self._api_client.job_get(job_id)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeJobNotFound(f"Job not found: {ex.message}") from None
            raise QiskitRuntimeError(f"Failed to delete job: {ex}") from None
        return self._decode_job(response)

    def jobs(
        self,
        limit: Optional[int] = 10,
        skip: int = 0,
        pending: bool = None,
        program_id: str = None,
        hub: str = None,
        group: str = None,
        project: str = None,
    ) -> List[RuntimeJob]:
        """Retrieve all runtime jobs, subject to optional filtering.

        Args:
            limit: Number of jobs to retrieve. ``None`` means no limit.
            skip: Starting index for the job retrieval.
            pending: Filter by job pending state. If ``True``, 'QUEUED' and 'RUNNING'
                jobs are included. If ``False``, 'DONE', 'CANCELLED' and 'ERROR' jobs
                are included.
            program_id: Filter by Program ID.
            hub: Filter by hub - hub, group, and project must all be specified.
            group: Filter by group - hub, group, and project must all be specified.
            project: Filter by project - hub, group, and project must all be specified.

        Returns:
            A list of runtime jobs.

        Raises:
            IBMInputValueError: If any but not all of the parameters ``hub``, ``group``
                and ``project`` are given.
        """
        if any([hub, group, project]) and not all([hub, group, project]):
            raise IBMInputValueError(
                "Hub, group and project "
                "parameters must all be specified. "
                'hub = "{}", group = "{}", project = "{}"'.format(hub, group, project)
            )
        job_responses = []  # type: List[Dict[str, Any]]
        current_page_limit = limit or 20
        offset = skip

        while True:
            jobs_response = self._api_client.jobs_get(
                limit=current_page_limit,
                skip=offset,
                pending=pending,
                program_id=program_id,
                hub=hub,
                group=group,
                project=project,
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
            QiskitRuntimeError: If the request failed.
        """
        try:
            self._api_client.job_delete(job_id)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                raise RuntimeJobNotFound(f"Job not found: {ex.message}") from None
            raise QiskitRuntimeError(f"Failed to delete job: {ex}") from None

    def _decode_job(self, raw_data: Dict) -> RuntimeJob:
        """Decode job data received from the server.

        Args:
            raw_data: Raw job data received from the server.

        Returns:
            Decoded job data.
        """
        hub = raw_data["hub"]
        group = raw_data["group"]
        project = raw_data["project"]
        # Try to find the right backend
        try:
            backend = self.get_backend(
                raw_data["backend"], hub=hub, group=group, project=project
            )
        except (IBMProviderError, QiskitBackendNotFoundError):
            backend = ibm_backend.IBMRetiredBackend.from_name(
                backend_name=raw_data["backend"],
                service=self,
                credentials=Credentials(
                    token="", url="", hub=hub, group=group, project=project
                ),
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
            credentials=self._default_hgp.credentials,
            job_id=raw_data["id"],
            program_id=raw_data.get("program", {}).get("id", ""),
            params=decoded,
            creation_date=raw_data.get("created", None),
        )

    def logout(self) -> None:
        """Clears authorization cache on the server.

        For better performance, the runtime server caches each user's
        authorization information. This method is used to force the server
        to clear its cache.

        Note:
            Invoke this method ONLY when your access level to the runtime
            service has changed - for example, the first time your account is
            given the authority to upload a program.
        """
        self._api_client.logout()

    def __repr__(self) -> str:
        return "<{}>".format(self.__class__.__name__)
