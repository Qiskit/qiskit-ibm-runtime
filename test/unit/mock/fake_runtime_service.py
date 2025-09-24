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

from typing import List, Optional, Tuple
from unittest import mock

from qiskit_ibm_runtime.accounts import Account
from qiskit_ibm_runtime.api.exceptions import RequestsApiError
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService, RuntimeClient
from .fake_runtime_client import BaseFakeRuntimeClient
from .fake_api_backend import FakeApiBackendSpecs


class FakeRuntimeService(QiskitRuntimeService):
    """Creates an QiskitRuntimeService instance with mocked instance crn.

    By default there are 2 instance crns:
    `crn:v1:bluemix:public:quantum-computing:my-region:a/crn1:...::`,
    and `crn:v1:bluemix:public:quantum-computing:my-region:a/crn2:...::`.
    Each crn has 2 backends - `common_backend` and `unique_backend_<idx>`.
    """

    DEFAULT_CRNS = [
        "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
        "crn:v1:bluemix:public:quantum-computing:my-region:a/crn1:...::",
        "crn:v1:bluemix:public:quantum-computing:my-region:a/crn2:...::",
    ]
    DEFAULT_COMMON_BACKEND = "common_backend"
    DEFAULT_UNIQUE_BACKEND_PREFIX = "unique_backend_"
    DEFAULT_INSTANCES = [
        {
            "crn": "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
            "tags": ["services"],
            "name": "test-instance",
            "pricing_type": "free",
            "plan": "internal",
        }
    ]

    def __new__(cls, *args, num_crns=2, runtime_client=None, backend_specs=None, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, num_crns=2, runtime_client=None, backend_specs=None, **kwargs):
        self._test_num_crns = num_crns
        self._fake_runtime_client = runtime_client
        self._backend_specs = backend_specs

        mock_runtime_client = mock.MagicMock()

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

    def instances(self):
        """Return a list of instances."""
        return self.DEFAULT_INSTANCES

    def _resolve_crn(self, account: Account) -> None:
        pass

    def _discover_backends_from_instance(self, instance: str) -> List[str]:
        """Mock discovery cloud backends."""
        job_class = self._active_api_client._job_classes  # type: ignore
        self._active_api_client = self._fake_runtime_client
        self._set_api_client(crns=[None] * self._test_num_crns, channel="ibm_quantum_platform")
        self._active_api_client._job_classes = job_class  # type: ignore
        return self._active_api_client.list_backends()  # type: ignore

    def _create_new_cloud_api_client(self, instance: str) -> None:
        """Create new api client."""
        pass

    def _get_crn_from_instance_name(self, account: Account, instance: str) -> str:
        # return dummy crn
        return instance

    def _get_api_client(self, instance: Optional[str] = None) -> RuntimeClient:
        return self._active_api_client

    def _resolve_cloud_instances(self, instance: Optional[str]) -> List[Tuple[str, List[str]]]:
        if instance:
            return [(instance, self._discover_backends_from_instance(instance))]
        if not self._all_instances:
            self._all_instances = self.DEFAULT_INSTANCES
        if not self._backend_instance_groups:
            self._backend_instance_groups = [
                {
                    "name": inst["name"],
                    "crn": inst["crn"],
                    "plan": inst.get("plan"),
                    "backends": self._discover_backends_from_instance(inst["crn"]),
                    "tags": inst.get("tags"),
                    "pricing_type": inst["pricing_type"],
                }
                for inst in self._all_instances
            ]
            self._filter_instances_by_saved_preferences()
        return [(inst["crn"], inst["backends"]) for inst in self._backend_instance_groups]

    def _set_api_client(self, crns, channel="ibm_quantum_platform"):
        """Set api client to be the fake runtime client."""
        if not self._fake_runtime_client:
            if not self._backend_specs:
                self._backend_specs = [
                    FakeApiBackendSpecs(backend_name=self.DEFAULT_COMMON_BACKEND, crns=crns)
                ]
                for idx, crn in enumerate(crns):
                    self._backend_specs.append(
                        FakeApiBackendSpecs(
                            backend_name=self.DEFAULT_UNIQUE_BACKEND_PREFIX + str(idx),
                            crns=[crn],
                        )
                    )
            self._fake_runtime_client = BaseFakeRuntimeClient(
                backend_specs=self._backend_specs, channel=channel
            )

        # Set fake runtime clients
        self._active_api_client = self._fake_runtime_client
