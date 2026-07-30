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

"""Custom ``responses`` registries for using with unit tests."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeAlias

from responses import GET, POST, CallbackResponse, Response
from responses.registries import FirstMatchRegistry

from qiskit_ibm_runtime.fake_provider import FakeLimaV2

if TYPE_CHECKING:
    from requests import PreparedRequest

    from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2

# ``responses`` callback return value: (status code, headers, body).
CallbackResult: TypeAlias = tuple[int, dict[str, str], str]

PricingType: TypeAlias = Literal["free", "trial", "paygo", "paid", "subscription", "unknown"]

DEFAULT_BACKED_CONFIGURATION = FakeLimaV2()._load_json(FakeLimaV2.conf_filename)
"""Default configuration for registry backends, cached and based on FakeLima."""

DEFAULT_BACKED_PROPERTIES = FakeLimaV2()._load_json(FakeLimaV2.props_filename)
"""Default properties for registry backends, cached and based on FakeLima."""


@dataclass
class Instance:
    """Registry representation of an instance."""

    name: str
    """Name of the instance."""

    crn: str = ""
    """CRN of the instance. If not set, will be automatically initialized."""

    allocations: int = 42
    """Allocations of the instance."""

    pricing_type: PricingType = "free"
    """Pricing type of the instance."""

    def __post_init__(self) -> None:
        if not self.crn:
            self.crn = f"crn:v1:bluemix:public:quantum-computing:my-region:{self.name}/...:...::"


@dataclass
class Backend:
    """Registry representation of a backend."""

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
            self.configuration = DEFAULT_BACKED_CONFIGURATION.copy()
            self.configuration["backend_name"] = self.name

        if not self.properties:
            self.properties = DEFAULT_BACKED_PROPERTIES.copy()
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


class BaseRegistry(FirstMatchRegistry):
    """Registry that dynamically serves IBM Quantum Compute responses.

    Registry for ``responses`` that generates mocked HTTP responses that allow for testing a subset
    of the functionality of ``QiskitRuntimeService``. The responses are generated dynamically via
    the ``callback_*`` methods of this class.

    The content of the responses is controlled via the ``instances`` and ``backends`` attributes,
    which can be modified via ``add_instance()`` and ``add_backends()``.

    .. seealso::
        ``decorators.mock_responses`` for a decorator that enables and passes the registry to
        unit tests.

        This class' subclasses for examples of convenient pre-populated registries.

    .. note::
        The registry is not meant to provide a full substitute of IBM Quantum Compute API, or
        return full responses. It is tailored to the needs of testing.
    """

    instances: dict[str, Instance]
    """Instances in this registry, keyed by instance name."""

    backends: dict[str, dict[str, Backend]]
    """Backends in this registry, keyed by instance name."""

    def __init__(self) -> None:
        super().__init__()

        self.instances = {}
        self.backends = defaultdict(dict)

        # Add callbacks for IBM Global Search and Global Catalog.
        self.add(
            CallbackResponse(
                method=POST,
                url="https://api.global-search-tagging.cloud.ibm.com/v3/resources/search",
                callback=self.callback_global_search,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                url=re.compile(r"https://globalcatalog.cloud.ibm.com/api/v1/\w+"),
                callback=self.callback_catalog,
            )
        )

        # Add callbacks for the IBM Quantum Compute `/backends` endpoints.
        self.add(
            CallbackResponse(
                method=GET,
                url="https://my-region.quantum.cloud.ibm.com/api/v1/backends",
                callback=self.callback_backends,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                url=re.compile(
                    r"https://my-region.quantum.cloud.ibm.com/api/v1/backends/\w+/configuration"
                ),
                callback=self.callback_backends_configuration,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                url=re.compile(
                    r"https://my-region.quantum.cloud.ibm.com/api/v1/backends/\w+/properties"
                ),
                callback=self.callback_backends_properties,
            )
        )
        self.add(
            CallbackResponse(
                method=GET,
                url=re.compile(
                    r"https://my-region.quantum.cloud.ibm.com/api/v1/backends/\w+/status"
                ),
                callback=self.callback_backends_status,
            )
        )

        # Add responses for the IBM Quantum Compute `/instances` endpoint.
        self.add(
            Response(
                method=GET,
                url="https://my-region.quantum.cloud.ibm.com/api/v1/instances/usage",
                json={},
            )
        )

        # Add callbacks for the IBM Quantum Compute `/jobs` endpoints.
        self.add(
            CallbackResponse(
                method=POST,
                url="https://my-region.quantum.cloud.ibm.com/api/v1/jobs",
                callback=self.callback_jobs,
            ),
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

    def callback_global_search(self, _: PreparedRequest) -> CallbackResult:
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

    def callback_catalog(self, request: PreparedRequest) -> CallbackResult:
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

    def callback_backends(self, request: PreparedRequest) -> CallbackResult:
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

    def callback_backends_configuration(self, request: PreparedRequest) -> CallbackResult:
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

    def callback_backends_properties(self, request: PreparedRequest) -> CallbackResult:
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

    def callback_backends_status(self, request: PreparedRequest) -> CallbackResult:
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

    def callback_jobs(self, request: PreparedRequest) -> CallbackResult:
        """Callback for the IBM Quantum Compute API ``/jobs`` endpoint.

        Dynamically return a job, based on the contents of `self.backends`.

        References:
            https://quantum.cloud.ibm.com/docs/en/api/qiskit-runtime-rest/tags/jobs
        """
        # Validate the instance CRN and backend name.
        instance_crn = request.headers.get("Service-CRN")
        instance = next(
            instance for instance in self.instances.values() if instance.crn == instance_crn
        )
        backend_name = json.loads(str(request.body))["backend"]

        if instance.name not in self.backends or backend_name not in self.backends[instance.name]:
            return (404, {"Content-Type": "application/json"}, "{}")

        response_body = {
            "id": "12345",
            "backend": backend_name,
        }
        return (200, {"Content-Type": "application/json"}, json.dumps(response_body))


class DefaultRegistry(BaseRegistry):
    """Registry with two instances, with one common backend and two unique backends.

    This registry contains:
    * instance ``a`` (free plan): with ``common_backend``, and ``unique_backend_a``
    * instance ``b`` (trial plan): with ``common_backend``, and ``unique_backend_b``
    """

    def __init__(self) -> None:
        super().__init__()

        self.add_instance(Instance("a"))
        self.add_instance(Instance("b", pricing_type="trial"))
        self.add_backend(Backend("common_backend"))
        self.add_backend(Backend("unique_backend_a"), "a")
        self.add_backend(Backend("unique_backend_b"), "b")


class OneInstanceNoBackendsRegistry(BaseRegistry):
    """Registry pre-loaded with a single instance ``a`` with no backends.

    This registry contains:
    * instance ``a`` (free plan): no backends.
    """

    def __init__(self) -> None:
        super().__init__()

        self.add_instance(Instance("a"))
