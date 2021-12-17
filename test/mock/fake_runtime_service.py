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

from typing import Dict
from collections import OrderedDict
from unittest import mock

from qiskit_ibm_runtime.ibm_runtime_service import IBMRuntimeService
from qiskit_ibm_runtime.hub_group_project import HubGroupProject
from qiskit_ibm_runtime.api.client_parameters import ClientParameters

from .fake_account_client import BaseFakeAccountClient
from .fake_runtime_client import BaseFakeRuntimeClient


class FakeRuntimeService(IBMRuntimeService):
    """Creates an IBMRuntimeService instance with mocked hub/group/project.

    By default there are 2 h/g/p - `hub0/group0/project0` and `hub1/group1/project1`.
    Each h/g/p has 2 backends - `common_backend` and `unique_backend_<idx>`.
    """

    def __init__(self, *args, **kwargs):
        test_options = kwargs.pop("test_options", {})
        self._test_num_hgps = test_options.get("num_hgps", 2)
        test_options = {
            "backend_client": BaseFakeAccountClient(
                backend_names=["common_backend", "unique_backend_0"])
        }

        with mock.patch(
                "qiskit_ibm_runtime.ibm_runtime_service.RuntimeClient",
                new=BaseFakeRuntimeClient,
        ):
            super().__init__(*args, **kwargs)

        # self._api_client = test_options.get("api_client", BaseFakeRuntimeClient())

    def _initialize_hgps(
        self, client_params: ClientParameters
    ) -> Dict:
        """Mock hgp initialization."""

        hgps = OrderedDict()

        for idx in range(self._test_num_hgps):
            hgp_name = f"hub{idx}/group{idx}/project{idx}"

            hgp_params = ClientParameters(
                auth_type="legacy",
                token="some_token",
                url="some_url",
                instance=hgp_name,
            )
            hgp = HubGroupProject(client_params=hgp_params, instance=hgp_name)
            hgp._api_client = BaseFakeAccountClient(
                backend_names=["common_backend", f"unique_backend_{idx}"])
            hgps[hgp_name] = hgp

        return hgps

    def _discover_cloud_backends(self):
        """Mock discovery cloud backends."""
        test_options = {
            "backend_client": BaseFakeAccountClient(
                backend_names=["common_backend", "unique_backend_0"]),
            "auth_type": "cloud"
        }
        self._api_client = BaseFakeRuntimeClient(test_options=test_options)
        return super()._discover_cloud_backends()
