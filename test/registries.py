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

"""Custom ``responses`` registries used by unit tests."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeAlias

from responses import GET, POST, CallbackResponse
from responses.registries import FirstMatchRegistry

from qiskit_ibm_runtime.fake_provider import FakeLimaV2

if TYPE_CHECKING:
    from requests import PreparedRequest

    from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2

# ``responses`` callback return value: (status code, headers, body).
CallbackResult: TypeAlias = tuple[int, dict[str, str], str]

PricingType: TypeAlias = Literal["free", "trial", "paygo", "paid", "subscription", "unknown"]


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

    pricing_type: PricingType = "free"
    """Pricing type of the instance."""

    def __post_init__(self) -> None:
        if not self.crn:
            self.crn = (
                f"crn:v1:bluemix:public:quantum-computing:{self.region}:{self.name}/...:...::"
            )


@dataclass
class Backend:
    """Represents a backend."""

    name: str
    """Name of the backend."""

    configuration: dict = field(default_factory=dict)
    """Configuration of the backend. If not set, it will be set based on ``FakeLimaV2``."""

    properties: dict = field(default_factory=dict)
    """Properties of the backend. If not set, it will be set based on ``FakeLimaV2``."""

    status: Literal["online", "paused", "offline"] = "online"
    """Status of the backend."""

    queue_length: int = 0
    """Lenght of the queue for this backend."""

    def __post_init__(self) -> None:
        if not self.configuration:
            reference = FakeLimaV2()
            self.configuration = reference._load_json(reference.conf_filename)
            self.configuration["backend_name"] = self.name

        if not self.properties:
            reference = FakeLimaV2()
            self.properties = reference._load_json(reference.props_filename)
            self.properties["backend_name"] = self.name

    @classmethod
    def from_(
        cls,
        fake_backend: type[FakeBackendV2],
        name: str | None = None,
        status: Literal["online", "paused", "offline"] = "online",
        queue_length: int = 0,
    ) -> Backend:
        """Create a ``Backend`` with the configuration and properties of ``fake_backend``."""
        reference = fake_backend()
        configuration = reference._load_json(reference.conf_filename)
        properties = reference._load_json(reference.props_filename)
        if name:
            configuration["backend_name"] = name
            properties["backend_name"] = name

        return cls(
            name=configuration["backend_name"],
            configuration=configuration,
            properties=properties,
            status=status,
            queue_length=queue_length,
        )


class IBMQuantumComputeRegistry(FirstMatchRegistry):
    """Registry that dynamically serves IBM Quantum Compute responses.

    Instances and backends start empty; populate them with ``add_instance`` and
    ``add_backend`` (see ``DefaultRegistry`` for a pre-loaded subclass).
    """

    instances: dict[str, Instance]
    """Names of the instances."""

    backends: dict[str, dict[str, Backend]]
    """Backends in this registry, keyed by instance."""

    def __init__(self) -> None:
        super().__init__()

        self.instances = {}
        self.backends = defaultdict(dict)

        # Add callbacks for IBM Global Search and Global Catalog.
        self.add(
            CallbackResponse(
                method=POST,
                url="https://api.global-search-tagging.cloud.ibm.com/v3/resources/search",
                callback=self.global_search_callback,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                url=re.compile(r"https://globalcatalog.cloud.ibm.com/api/v1/\w+"),
                callback=self.catalog_callback,
            )
        )

        # Add callbacks for the IBM Quantum Compute `/backends` endpoints.
        self.add(
            CallbackResponse(
                method=GET,
                # TODO: take into account region, and validate.
                url="https://my-region.quantum.cloud.ibm.com/api/v1/backends",
                callback=self.backends_callback,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                # TODO: take into account region, and validate.
                url=re.compile(
                    r"https://my-region.quantum.cloud.ibm.com/api/v1/backends/\w+/configuration"
                ),
                callback=self.backends_configuration_callback,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                # TODO: take into account region, and validate.
                url=re.compile(
                    r"https://my-region.quantum.cloud.ibm.com/api/v1/backends/\w+/properties"
                ),
                callback=self.backends_properties_callback,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                # TODO: take into account region, and validate.
                url=re.compile(
                    r"https://my-region.quantum.cloud.ibm.com/api/v1/backends/\w+/status"
                ),
                callback=self.backends_status_callback,
            )
        )

    def add_instance(self, instance: Instance) -> None:
        """Add a new instance to the registry."""
        self.instances[instance.name] = instance

    def add_backend(self, backend: Backend, instance: str | None = None) -> None:
        """Add a new backend to the registry.

        If ``instance`` is not passed, the backend is added to all existing instances.
        """
        instances = [instance] if instance is not None else list(self.instances)
        for name in instances:
            self.backends[name][backend.name] = backend

    def global_search_callback(self, _: PreparedRequest) -> CallbackResult:
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

    def catalog_callback(self, request: PreparedRequest) -> CallbackResult:
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

    def backends_callback(self, request: PreparedRequest) -> CallbackResult:
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

        response_body = {
            "devices": [
                {
                    "name": backend.name,
                    "status": {"name": backend.status},
                    "queue_length": backend.queue_length,
                }
                for backend in self.backends[instance.name].values()
            ]
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))

    def backends_configuration_callback(self, request: PreparedRequest) -> CallbackResult:
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

        backend = self.backends[instance.name][backend_name]
        return (200, {"Content-Type": "application/json"}, json.dumps(backend.configuration))

    def backends_properties_callback(self, request: PreparedRequest) -> CallbackResult:
        """Callback for the IBM Quantum Compute API ``/backends/{id}/properties`` endpoint.

        Dynamically return the properties of a backend, based on the contents of `self.backends`.

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

        backend = self.backends[instance.name][backend_name]
        return (200, {"Content-Type": "application/json"}, json.dumps(backend.properties))

    def backends_status_callback(self, request: PreparedRequest) -> CallbackResult:
        """Callback for the IBM Quantum Compute API ``/backends/{id}/status`` endpoint.

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

        backend = self.backends[instance.name][backend_name]
        response_body = {
            "state": backend.status == "online",
            "status": "active" if backend.status == "online" else backend.status,
            "length_queue": backend.queue_length,
            "backend_version": backend.configuration["backend_version"],
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))


class DefaultRegistry(IBMQuantumComputeRegistry):
    """Registry pre-loaded with a default set of instances and backends."""

    def __init__(self) -> None:
        super().__init__()

        self.add_instance(Instance("a"))
        self.add_instance(Instance("b", pricing_type="trial"))
        self.add_backend(Backend("common_backend"))
        self.add_backend(Backend("unique_backend_a"), "a")
        self.add_backend(Backend("unique_backend_b"), "b")


class OneInstanceNoBackendsRegistry(IBMQuantumComputeRegistry):
    """Registry pre-loaded with a single instance ``a`` and no backends."""

    def __init__(self) -> None:
        super().__init__()

        self.add_instance(Instance("a"))
