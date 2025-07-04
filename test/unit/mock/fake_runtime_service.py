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

"""Context managers for using with IBM Provider unit tests."""

from collections import OrderedDict
from typing import Dict, List, Optional, Tuple
from unittest import mock

from qiskit_ibm_runtime.accounts import Account
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.clients import AuthClient
from qiskit_ibm_runtime.api.exceptions import RequestsApiError
from qiskit_ibm_runtime.hub_group_project import HubGroupProject
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from .fake_runtime_client import BaseFakeRuntimeClient
from .fake_api_backend import FakeApiBackendSpecs


class FakeRuntimeService(QiskitRuntimeService):
    """Creates an QiskitRuntimeService instance with mocked hub/group/project.

    By default there are 2 h/g/p - `hub0/group0/project0` and `hub1/group1/project1`.
    Each h/g/p has 2 backends - `common_backend` and `unique_backend_<idx>`.
    """

    DEFAULT_HGPS = ["hub0/group0/project0", "hub1/group1/project1"]
    DEFAULT_COMMON_BACKEND = "common_backend"
    DEFAULT_UNIQUE_BACKEND_PREFIX = "unique_backend_"
    DEFAULT_INSTANCES = [
        {
            "crn": "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
            "tags": ["services"],
        }
    ]

    def __new__(cls, *args, num_hgps=2, runtime_client=None, backend_specs=None, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, num_hgps=2, runtime_client=None, backend_specs=None, **kwargs):
        self._test_num_hgps = num_hgps
        self._fake_runtime_client = runtime_client
        self._backend_specs = backend_specs

        mock_runtime_client = mock.MagicMock()
        if kwargs.get("channel", "ibm_quantum") == "ibm_quantum":
            instance = kwargs.get("instance", "hub0/group0/project0")
        else:
            instance = kwargs.get(
                "instance", "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::"
            )

        mock_runtime_client._instance = instance
        mock_runtime_client.job_get = mock.MagicMock()
        mock_runtime_client.job_get.side_effect = RequestsApiError("Job not found", status_code=404)

        with mock.patch(
            "qiskit_ibm_runtime.qiskit_runtime_service.RuntimeClient",
            return_value=mock_runtime_client,
        ):
            super().__init__(*args, **kwargs)

        # Use default if api client is somehow not set.
        if not isinstance(self._active_api_client, BaseFakeRuntimeClient):
            self._active_api_client = self._fake_runtime_client or BaseFakeRuntimeClient(
                backend_specs=self._backend_specs, instance=instance
            )

    def _authenticate_ibm_quantum_account(
        self, client_params: ClientParameters
    ) -> "FakeAuthClient":
        """Mock authentication."""
        return FakeAuthClient()

    def _resolve_crn(self, account: Account) -> None:
        pass

    def _initialize_hgps(
        self,
        auth_client: AuthClient,
    ) -> Dict:
        """Mock hgp initialization.

        By default there are 2 h/g/p - `hub0/group0/project0` and `hub1/group1/project1`.
        Each h/g/p has 2 backends - `common_backend` and `unique_backend_<idx>`.
        """

        hgps = OrderedDict()

        for idx in range(self._test_num_hgps):
            hgp_name = self.DEFAULT_HGPS[idx]

            hgp_params = ClientParameters(
                channel="ibm_quantum",
                token="some_token",
                url="some_url",
                instance=hgp_name,
            )
            hgp = HubGroupProject(client_params=hgp_params, instance=hgp_name, service=self)

            hgps[hgp_name] = hgp

        # Set fake runtime clients
        self._set_api_client(hgps=list(hgps.keys()))
        for hgp in hgps.values():
            hgp._runtime_client = self._active_api_client

        return hgps

    def _discover_backends_from_instance(self, instance: str) -> List[str]:
        """Mock discovery cloud backends."""
        job_class = self._active_api_client._job_classes  # type: ignore
        self._active_api_client = self._fake_runtime_client
        self._set_api_client(hgps=[None] * self._test_num_hgps, channel="ibm_quantum_platform")
        self._active_api_client._job_classes = job_class  # type: ignore
        return self._active_api_client.list_backends()

    def _create_new_cloud_api_client(self, instance: str) -> None:
        """Create new api client."""
        pass

    def _get_crn_from_instance_name(self, account: Account, instance: str) -> str:
        # return dummy crn
        return instance

    def _resolve_cloud_instances(self, instance: Optional[str]) -> List[Tuple[str, List[str]]]:
        if instance:
            return [(instance, self._discover_backends_from_instance(instance))]
        if not self._all_instances:
            self._all_instances = self.DEFAULT_INSTANCES
        if not self._backend_instance_groups:
            self._backend_instance_groups = [
                {
                    "crn": inst["crn"],
                    "plan": inst.get("plan"),
                    "backends": self._discover_backends_from_instance(inst["crn"]),
                    "tags": inst.get("tags"),
                }
                for inst in self._all_instances
            ]
            self._filter_instances_by_saved_preferences()
        return [(inst["crn"], inst["backends"]) for inst in self._backend_instance_groups]

    def _set_api_client(self, hgps, channel="ibm_quantum"):
        """Set api client to be the fake runtime client."""
        if not self._fake_runtime_client:
            if not self._backend_specs:
                self._backend_specs = [
                    FakeApiBackendSpecs(backend_name=self.DEFAULT_COMMON_BACKEND, hgps=hgps)
                ]
                for idx, hgp in enumerate(hgps):
                    self._backend_specs.append(
                        FakeApiBackendSpecs(
                            backend_name=self.DEFAULT_UNIQUE_BACKEND_PREFIX + str(idx),
                            hgps=[hgp],
                        )
                    )
            self._fake_runtime_client = BaseFakeRuntimeClient(
                backend_specs=self._backend_specs, channel=channel
            )

        # Set fake runtime clients
        self._active_api_client = self._fake_runtime_client


class FakeAuthClient(AuthClient):
    """Fake auth client."""

    def __init__(self):  # pylint: disable=super-init-not-called
        # Avoid calling parent __init__ method. It has side-effects that are not supported in unit tests.
        pass

    def current_service_urls(self):
        """Return service urls."""
        return {
            "http": "IBM_QUANTUM_API_URL",
            "services": {"runtime": "ibm_quantum_runtime_url"},
        }

    def current_access_token(self):
        """Return access token."""
        return "some_token"
