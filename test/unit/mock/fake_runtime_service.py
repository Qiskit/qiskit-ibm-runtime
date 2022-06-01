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
from typing import Dict, Any
from unittest import mock

from qiskit_ibm_runtime.accounts import Account
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.clients import AuthClient
from qiskit_ibm_runtime.hub_group_project import HubGroupProject
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from .fake_account_client import BaseFakeAccountClient
from .fake_runtime_client import BaseFakeRuntimeClient


class FakeRuntimeService(QiskitRuntimeService):
    """Creates an QiskitRuntimeService instance with mocked hub/group/project.

    By default there are 2 h/g/p - `hub0/group0/project0` and `hub1/group1/project1`.
    Each h/g/p has 2 backends - `common_backend` and `unique_backend_<idx>`.

    There are a few test options available, via the `test_options` input:

        - num_hgps: Number of hub/group/project.
        - account_client: Custom account (backend) client to use.
    """

    DEFAULT_HGPS = ["hub0/group0/project0", "hub1/group1/project1"]
    DEFAULT_COMMON_BACKEND = "common_backend"
    DEFAULT_UNIQUE_BACKEND_PREFIX = "unique_backend_"

    def __init__(self, *args, **kwargs):
        test_options = kwargs.pop("test_options", {})
        self._test_num_hgps = test_options.get("num_hgps", 2)
        self._fake_account_client = test_options.get("account_client")

        with mock.patch(
            "qiskit_ibm_runtime.qiskit_runtime_service.RuntimeClient",
            new=BaseFakeRuntimeClient,
        ):
            super().__init__(*args, **kwargs)

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
        """Mock hgp initialization."""

        hgps = OrderedDict()

        for idx in range(self._test_num_hgps):
            hgp_name = self.DEFAULT_HGPS[idx]

            hgp_params = ClientParameters(
                channel="ibm_quantum",
                token="some_token",
                url="some_url",
                instance=hgp_name,
            )
            hgp = HubGroupProject(
                client_params=hgp_params, instance=hgp_name, service=self
            )
            fake_account_client = self._fake_account_client
            if not fake_account_client:
                specs = [
                    {"configuration": {"backend_name": self.DEFAULT_COMMON_BACKEND}},
                    {
                        "configuration": {
                            "backend_name": self.DEFAULT_UNIQUE_BACKEND_PREFIX
                            + str(idx)
                        }
                    },
                ]
                fake_account_client = BaseFakeAccountClient(specs=specs, hgp=hgp_name)
            hgp._api_client = fake_account_client
            hgps[hgp_name] = hgp

        return hgps

    def _discover_cloud_backends(self):
        """Mock discovery cloud backends."""
        if not self._fake_account_client:
            specs = [{"configuration": {"backend_name": self.DEFAULT_COMMON_BACKEND}}]
            for idx in range(self._test_num_hgps):
                specs.append(
                    {
                        "configuration": {
                            "backend_name": self.DEFAULT_UNIQUE_BACKEND_PREFIX
                            + str(idx)
                        }
                    }
                )
            self._fake_account_client = BaseFakeAccountClient(specs=specs)

        test_options = {
            "backend_client": self._fake_account_client,
            "channel": "ibm_cloud",
        }
        self._api_client = BaseFakeRuntimeClient(test_options=test_options)
        return super()._discover_cloud_backends()


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
