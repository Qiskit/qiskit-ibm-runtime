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

import json
import logging
import re
import traceback
import warnings
from collections import OrderedDict
from typing import Dict, Callable, Optional, Union, List, Any, Type

from qiskit.providers.backend import BackendV1 as Backend
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends

from .accounts import AccountManager, Account, AccountType
from qiskit_ibm_runtime import ibm_backend  # pylint: disable=unused-import
from .api.clients import AuthClient, VersionClient
from .api.clients.runtime import RuntimeClient
from .api.exceptions import RequestsApiError
from .constants import QISKIT_IBM_RUNTIME_API_URL
from .credentials import Credentials
from .exceptions import IBMNotAuthorizedError, IBMInputValueError, IBMProviderError
from .exceptions import (
    QiskitRuntimeError,
    RuntimeDuplicateProgramError,
    RuntimeProgramNotFound,
    RuntimeJobNotFound,
    IBMProviderCredentialsInvalidUrl,
)
from .hub_group_project import HubGroupProject  # pylint: disable=cyclic-import
from .program.result_decoder import ResultDecoder
from .runtime_job import RuntimeJob
from .runtime_program import RuntimeProgram, ParameterNamespace
from .utils import RuntimeDecoder, to_base64_string, to_python_identifier
from .utils.backend_decoder import configuration_from_server_data
from .utils.hgp import to_instance_format, from_instance_format
from .api.client_parameters import ClientParameters

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
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        auth: Optional[AccountType] = None,
        name: Optional[str] = None,
        proxies: Optional[dict] = None,
        verify: bool = True,
    ) -> None:
        """IBMRuntimeService constructor

        Args:
            token: IBM Cloud API key or IBM Quantum API token.
            url: The API URL.
                Defaults to https://cloud.ibm.com (cloud) or
                https://auth.quantum-computing.ibm.com/api (legacy).
            instance: The CRN (cloud) or hub/group/project (legacy).
            auth: Authentication type. `cloud` or `legacy`.
            name: Name of the account to load.
            proxies: Proxy configuration for the server.
            verify: Verify the server's TLS certificate.

        Returns:
            An instance of IBMRuntimeService.
        """
        super().__init__()

        # TODO: add support for loading default account when optional parameters are not set
        #  i.e. fallback to environment variables
        #  i.e. fallback to default account saved on disk
        self._account = (
            AccountManager.get(name=name)
            if name
            else Account(
                auth=auth,
                token=token,
                url=url,
                instance=instance,
                proxies=proxies,
                verify=verify,
            )
        )

        self._client_params = ClientParameters(
            auth_type=self._account.auth,
            token=self._account.token,
            url=self._account.url,
            instance=self._account.instance,
            proxies=self._account.proxies,
            verify=self._account.verify,
        )

        self._auth = self._account.auth
        self._programs: Dict[str, RuntimeProgram] = {}
        self._backends: Dict[str, "ibm_backend.IBMBackend"] = {}
        self._api_client = RuntimeClient(self._client_params)

        if auth == "cloud":
            # TODO: We can make the backend discovery lazy
            self._backends = self._discover_cloud_backends()
            return
        else:
            self._hgps = self._initialize_hgps(self._client_params)
            for hgp in self._hgps.values():
                for name, backend in hgp.backends.items():
                    if name not in self._backends:
                        self._backends[name] = backend

        # self._discover_backends()

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
            # TODO: pass instance
            config = configuration_from_server_data(raw_config=raw_config)
            if not config:
                continue
            backend_cls = (
                ibm_backend.IBMSimulator
                if config.simulator
                else ibm_backend.IBMBackend
            )
            ret[config.backend_name] = backend_cls(
                configuration=config,
                api_client=self._api_client,
            )

        return ret

    def _initialize_hgps(
        self, client_params: ClientParameters
    ) -> Dict:
        """Authenticate against IBM Quantum and populate the hub/group/projects.

        Args:
            client_params: Parameters used for server connection.

        Raises:
            IBMProviderCredentialsInvalidUrl: If the URL specified is not
                a valid IBM Quantum authentication URL.
            IBMProviderError: If no hub/group/project could be found for this account.

        Returns:
            The hub/group/projects for this account.
        """
        hgps: OrderedDict[str, HubGroupProject] = OrderedDict()
        version_info = self._check_api_version(client_params)
        # Check the URL is a valid authentication URL.
        if not version_info["new_api"] or "api-auth" not in version_info:
            raise IBMProviderCredentialsInvalidUrl(
                "The URL specified ({}) is not an IBM Quantum authentication URL. "
                "Valid authentication URL: {}.".format(
                    client_params.url, QISKIT_IBM_RUNTIME_API_URL
                )
            )
        auth_client = AuthClient(client_params)
        service_urls = auth_client.current_service_urls()
        user_hubs = auth_client.user_hubs()
        for hub_info in user_hubs:
            # Build credentials.
            if not service_urls.get("services", {}).get("runtime"):
                # Skip those that don't support runtime.
                continue
            hgp_params = ClientParameters(
                auth_type=self._account.auth,
                token=auth_client.current_access_token(),
                url=service_urls["http"],
                instance=to_instance_format(hub_info["hub"], hub_info["group"], hub_info["project"]),
                proxies=client_params.proxies,
                verify=client_params.verify
            )

            # Build the hgp.
            try:
                hgp = HubGroupProject(
                    client_params=hgp_params,
                    instance=hgp_params.instance
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
            raise IBMProviderError(
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
                warnings.warn(f"Default hub/group/project {default_hgp} not "
                              "found for the account and is ignored.")
        return hgps

    @staticmethod
    def _check_api_version(
            params: ClientParameters
    ) -> Dict[str, Union[bool, str]]:
        """Check the version of the remote server in a set of credentials.

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
            backend_name: Optional[str] = None,
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
        """
        if instance:
            _ = from_instance_format(instance)  # Verify format
            if instance not in self._hgps:
                raise IBMInputValueError(f"Hub/group/project {instance} "
                                         "could not be found for this account.")
            if backend_name and not self._hgps[instance].get_backend(backend_name):
                raise IBMInputValueError(f"Backend {backend_name} cannot be found in "
                                         f"hub/group/project {instance}")
            return self._hgps[instance]

        if not backend_name:
            return list(self._hgps.values())[0]

        for hgp in self._hgps.values():
            if hgp.get_backend(backend_name):
                return hgp

        raise IBMInputValueError(f"Backend {backend_name} cannot be found in any"
                                 f"hub/group/project for this account.")

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
        instance: Optional[str] = None,
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
            instance: The service instance to use. For cloud runtime, this is the Cloud Resource
                Name (CRN). For legacy runtime, this is the hub/group/project in that format.
            kwargs: Simple filters that specify a ``True``/``False`` criteria in the
                backend configuration, backends status, or provider credentials.
                An example to get the operational backends with 5 qubits::

                    IBMRuntimeService.backends(n_qubits=5, operational=True)

        Returns:
            The list of available backends that match the filter.
        """
        if self._auth == "legacy":
            if instance:
                backends = list(self._get_hgp(instance=instance).backends.values())
            else:
                backends = list(self._backends.values())
        else:
            # TODO filtering by instance for cloud
            backends = list(self._backends.values())

        if name:
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

    def active_account(self) -> Optional[Dict[str, str]]:
        """Return the IBM Quantum account currently in use for the session.

        Returns:
            A dictionary with information about the account currently in the session.
        """
        return self._account.to_saved_format()

    @staticmethod
    def delete_account(name: Optional[str]) -> bool:
        """Delete a saved account from disk.

        Args:
            name: Custom name of the saved account. Defaults to "default".

        Returns:
            True if the account with the given name was deleted.
            False if no account was found for the given name.
        """

        return AccountManager.delete(name=name)

    @staticmethod
    def save_account(
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        auth: Optional[AccountType] = None,
        name: Optional[str] = None,
        proxies: Optional[dict] = None,
        verify: Optional[bool] = None,
    ) -> None:
        """Save the account to disk for future use.

        Args:
            token: IBM Cloud API key or IBM Quantum API token.
            url: The API URL.
                Defaults to https://cloud.ibm.com (cloud) or
                https://auth.quantum-computing.ibm.com/api (legacy).
            instance: The CRN (cloud) or hub/group/project (legacy).
            auth: Authentication type. `cloud` or `legacy`.
            name: Name of the account to save.
            proxies: Proxy configuration for the server.
            verify: Verify the server's TLS certificate.
        """

        return AccountManager.save(
            token=token,
            url=url,
            instance=instance,
            auth=auth,
            name=name,
            proxies=proxies,
            verify=verify,
        )

    @staticmethod
    def saved_accounts() -> dict:
        """List the accounts saved on disk.

        Returns:
            A dictionary with information about the accounts saved on disk.

        Raises:
            IBMProviderCredentialsInvalidUrl: If invalid IBM Quantum
                credentials are found on disk.
        """
        return AccountManager.list()

    def get_backend(
        self,
        name: str = None,
        instance: Optional[str] = None,
    ) -> Backend:
        """Return a single backend matching the specified filtering.

        Args:
            name: Name of the backend.
            instance: The service instance to use. For cloud runtime, this is the Cloud Resource
                Name (CRN). For legacy runtime, this is the hub/group/project in that format.

        Returns:
            Backend: A backend matching the filtering.

        Raises:
            QiskitBackendNotFoundError: if no backend could be found.
        """
        # pylint: disable=arguments-differ
        backends = self.backends(name, instance=instance)
        if not backends:
            raise QiskitBackendNotFoundError("No backend matches the criteria")
        return backends[0]

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
                for prog_dict in program_page:
                    program = self._to_program(prog_dict)
                    self._programs[program.program_id] = program
                if len(self._programs) == count:
                    # Stop if there are no more programs returned by the server.
                    break
                offset += len(program_page)
        if limit is None:
            limit = len(self._programs)
        return list(self._programs.values())[skip: limit + skip]

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
        image: str = "",
        instance: Optional[str] = None
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
            instance: The service instance to use. For cloud runtime, this is the Cloud Resource
                Name (CRN). For legacy runtime, this is the hub/group/project in that format.

        Returns:
            A ``RuntimeJob`` instance representing the execution.

        Raises:
            IBMInputValueError: If input is invalid.
        """
        # If using params object, extract as dictionary
        if isinstance(inputs, ParameterNamespace):
            inputs.validate()
            inputs = vars(inputs)

        if image and not re.match(
            "[a-zA-Z0-9]+([/.\\-_][a-zA-Z0-9]+)*:[a-zA-Z0-9]+([.\\-_][a-zA-Z0-9]+)*$",
            image,
        ):
            raise IBMInputValueError('"image" needs to be in form of image_name:tag')

        backend_name = options.get("backend_name", "")

        hgp_name = None
        if self._auth == "legacy":
            if not backend_name:
                raise IBMInputValueError(
                    '"backend_name" is required field in "options" for legacy runtime.')
            # Find the right hgp
            hgp = self._get_hgp(instance=instance, backend_name=backend_name)
            backend = hgp.get_backend(backend_name)
            hgp_name = hgp.name
        else:
            # TODO Support instance for cloud
            backend = self.get_backend(backend_name)

        result_decoder = result_decoder or ResultDecoder
        response = self._api_client.program_run(
            program_id=program_id,
            backend_name=backend_name,
            params=inputs,
            image=image,
            hgp=hgp_name
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
            QiskitRuntimeError: If the upload failed.
        """
        program_metadata = self._read_metadata(metadata=metadata)

        for req in ["name", "max_execution_time"]:
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
        instance: Optional[str] = None
    ) -> List[RuntimeJob]:
        """Retrieve all runtime jobs, subject to optional filtering.

        Args:
            limit: Number of jobs to retrieve. ``None`` means no limit.
            skip: Starting index for the job retrieval.
            pending: Filter by job pending state. If ``True``, 'QUEUED' and 'RUNNING'
                jobs are included. If ``False``, 'DONE', 'CANCELLED' and 'ERROR' jobs
                are included.
            program_id: Filter by Program ID.
            instance: The service instance to use. Currently only supported for legacy runtime,
                and should be in the hub/group/project.

        Returns:
            A list of runtime jobs.
        """
        hub = group = project = None
        if instance:
            if self._auth == "cloud":
                raise IBMInputValueError("'instance' is not supported by cloud runtime.")
            hub, group, project = from_instance_format(instance)

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
        instance = to_instance_format(hub, group, project) if all([hub, group, project]) else None
        # Try to find the right backend
        try:
            backend = self.get_backend(
                raw_data["backend"], instance=instance
            )
        except (IBMProviderError, QiskitBackendNotFoundError):
            backend = ibm_backend.IBMRetiredBackend.from_name(
                backend_name=raw_data["backend"],
                credentials=Credentials(
                    auth="legacy",
                    token="",
                    url="",
                    hub=hub,
                    group=group,
                    project=project,
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
            client_params=self._client_params,
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

    @property
    def auth(self) -> str:
        """Return the authentication type used.

        Returns:
            The authentication type used.
        """
        return self._auth

    def __repr__(self) -> str:
        return "<{}>".format(self.__class__.__name__)
