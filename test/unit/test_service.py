# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test QiskitRuntimeService."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Literal
from unittest.mock import patch

import responses
from ibm_cloud_sdk_core import IAMTokenManager
from ibm_cloud_sdk_core.authenticators import NoAuthAuthenticator
from responses.registries import FirstMatchRegistry

from qiskit_ibm_runtime.accounts.account import CloudAccount
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..ibm_test_case import IBMTestCase

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class Instance:
    """Represents an instance."""

    name: str
    """Name of the instance."""

    crn: str = ""
    """CRN of the instance. If not set, will be automatically initialized."""

    region: str = "my-region"
    """Region of the instance."""

    allocations: int = 42
    """Allocations of the instance."""

    pricing_type: Literal["free", "trial", "paygo", "paid", "subscription", "unknown"] = "free"
    """Pricing type of the instance."""

    def __post_init__(self):
        if not self.crn:
            self.crn = (
                f"crn:v1:bluemix:public:quantum-computing:{self.region}:{self.name}/...:...::"
            )


class IBMQuantumComputeRegistry(FirstMatchRegistry):
    """Registry pre-loaded with the responses for a service with a single backend."""

    instances: dict[str, Instance]
    """Names of the instances."""

    backends: dict[str, list[str]]
    """Names of the backends in this registry, keyed by instance."""

    def add_instance(
        self,
        name: str,
        pricing_type: Literal["free", "trial", "paygo", "paid", "subscription", "unknown"] = "free",
    ) -> None:
        """Add a new instance to the registry."""
        self.instances[name] = Instance(name=name, pricing_type=pricing_type)

    def add_backend(self, name: str, instance: str) -> None:
        """Add a new backend to the registry."""
        self.backends[instance].append(name)

    def global_search_callback(self, _):
        """Callback for the IBM Cloud Global Search API.

        Dynamically return a query that represents the list of instances, based on the contents of
        `self.instances`.

        References:
            https://cloud.ibm.com/docs/apis/search
            https://cloud.ibm.com/docs/apis/search.json
        """
        response_body = {
            "items": [
                {
                    "crn": instance.crn,
                    "name": instance.name,
                    "doc": {"extensions": instance.allocations},
                    "service_plan_unique_id": instance.name,
                }
                for _, instance in self.instances.items()
            ]
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))

    def catalog_callback(self, request):
        """Callback for the IBM Cloud API Global Catalog API.

        Dynamically return information about each instance, based on the contents of
        `self.instances`.

        References:
            https://cloud.ibm.com/docs/apis/resource-catalog/private-catalog
            https://cloud.ibm.com/docs/apis/resource-catalog/private-catalog.json
        """
        instance = self.instances[request.path_url.split("/")[-1]]
        response_body = {
            "overview_ui": {"en": {"display_name": instance.name}},
            "metadata": {"pricing": {"type": instance.pricing_type}},
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))

    def backends_callback(self, request):
        """Callback for the IBM Quantum Compute API ``/backends`` endpoint.

        Dynamically return the list of backends, based on the contents of `self.backends`.

        References:
            https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/backends
        """
        # Validate the instance CRN.
        instance_crn = request.headers.get("Service-CRN")
        instance = next(
            instance for instance in self.instances.values() if instance.crn == instance_crn
        )
        if instance.name not in self.backends:
            return (404, {"Content-Type": "application/json"}, "{}")

        response_body = {"devices": [{"name": backend} for backend in self.backends[instance.name]]}
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))

    def backends_configuration_callback(self, request):
        """Callback for the IBM Quantum Compute API ``/backends/{id}/configuration`` endpoint.

        Dynamically return the configuration of a backend, based on the contents of `self.backends`.

        References:
            https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/backends
        """
        # Validate the instance CRN and backend name.
        instance_crn = request.headers.get("Service-CRN")
        instance = next(
            instance for instance in self.instances.values() if instance.crn == instance_crn
        )
        backend_name = request.path_url.split("/")[4]
        if instance.name not in self.backends or backend_name not in self.backends[instance.name]:
            return (404, {"Content-Type": "application/json"}, "{}")

        response_body = {
            "backend_name": backend_name,
            "backend_version": "1.0",
            "online_date": "2020-03-23T04:00:00Z",
            "gates": [],
            "basis_gates": [],
            "n_qubits": 2,
            "local": False,
            "simulator": False,
            "conditional": True,
            "open_pulse": False,
            "memory": False,
            "coupling_map": [],
        }

        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))

    def __init__(self) -> None:
        super().__init__()

        self.instances = {}
        self.backends = defaultdict(list)

        self.add_instance("a")
        self.add_instance("b", "trial")
        self.add_backend("common_backend", "a")
        self.add_backend("common_backend", "b")
        self.add_backend("unique_backend", "b")

        # Add callbacks for IBM Global Search and Global Catalog.
        self.add(
            responses.CallbackResponse(
                method="POST",
                url="https://api.global-search-tagging.cloud.ibm.com/v3/resources/search",
                callback=self.global_search_callback,
            )
        )
        self.add(
            responses.CallbackResponse(
                method="GET",
                url=re.compile(r"https://globalcatalog.cloud.ibm.com/api/v1/\w+"),
                callback=self.catalog_callback,
            )
        )

        # Add callbacks for the IBM Quantum Compute `/backends` endpoints.
        self.add(
            responses.CallbackResponse(
                method="GET",
                # TODO: take into account region, and validate.
                url="https://my-region.quantum.cloud.ibm.com/api/v1/backends",
                callback=self.backends_callback,
            )
        )
        self.add(
            responses.CallbackResponse(
                method="GET",
                # TODO: take into account region, and validate.
                url=re.compile(
                    r"https://my-region.quantum.cloud.ibm.com/api/v1/backends/\w+/configuration"
                ),
                callback=self.backends_configuration_callback,
            )
        )


def mock_authentication(
    func_or_registry: Callable | type[FirstMatchRegistry] = IBMQuantumComputeRegistry,
) -> Callable:
    """Patch out IAM authentication and mock HTTP responses using a registry.

    Can be used bare (``@mock_authentication``, using the default registry) or
    called with a registry class (``@mock_authentication(SomeRegistry)``). The
    instantiated registry is passed to the wrapped test as an extra argument.
    """
    # Bare use: the argument is the decorated test method, not a registry class.
    if not isinstance(func_or_registry, type):
        return mock_authentication(IBMQuantumComputeRegistry)(func_or_registry)

    registry = func_or_registry

    def decorator(test_method: Callable) -> Callable:
        @wraps(test_method)
        def wrapper(*args: object, **kwargs: object) -> object:
            with (
                # Patch authentication, in order to simplify flow.
                patch.object(
                    CloudAccount, "get_iam_authentificator", return_value=NoAuthAuthenticator()
                ),
                patch.object(IAMTokenManager, "get_token", return_value="bearer token"),
                # Patch HTTP responses, allowing using a custom registry.
                responses.RequestsMock(
                    registry=registry, assert_all_requests_are_fired=True
                ) as responses_mock,
            ):
                return test_method(*args, responses_mock.get_registry(), **kwargs)

        return wrapper

    return decorator


class TestQiskitRuntimeServiceCase(IBMTestCase):
    """Tests for QiskitRuntimeService that use mocked HTTP responses."""

    @mock_authentication
    def test_authenticate_with_decorator(self, registry):
        """Test something."""
        service = QiskitRuntimeService(token="42")
        b = service.backends()
        print(b)
        print(service._backends_info_per_instance)
