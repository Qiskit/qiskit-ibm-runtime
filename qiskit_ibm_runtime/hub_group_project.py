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

"""A hub, group and project in an IBM Quantum account."""

import logging
from collections import OrderedDict
import traceback
from typing import Any, Dict, Optional

from qiskit.providers.backend import BackendV1 as Backend
from qiskit.providers.models import PulseBackendConfiguration, QasmBackendConfiguration
from qiskit_ibm_runtime import (  # pylint: disable=unused-import
    ibm_runtime_service,
    ibm_backend,
)

from .utils.json_decoder import decode_backend_configuration
from .api.clients import AccountClient
from .credentials import Credentials
from .exceptions import IBMInputValueError

logger = logging.getLogger(__name__)


class HubGroupProject:
    """Represents a hub/group/project with IBM Quantum backends and services associated with it."""

    def __init__(
        self,
        credentials: Credentials,
        service: "ibm_runtime_service.IBMRuntimeService",
        is_open: bool,
    ) -> None:
        """HubGroupProject constructor

        Args:
            credentials: IBM Quantum credentials.
            service: IBM Quantum account provider.
            is_open: True means open access, False means premium
        """
        self.credentials = credentials
        self._service = service
        self.is_open = is_open
        self._api_client = AccountClient(
            self.credentials, **self.credentials.connection_parameters()
        )
        # Initialize the internal list of backends.
        self._backends: Dict[str, "ibm_backend.IBMBackend"] = {}
        self._service_urls = {
            "backend": self.credentials.url,
            "experiment": self.credentials.experiment_url,
            "random": self.credentials.extractor_url,
            "runtime": self.credentials.runtime_url,
        }

    @property
    def backends(self) -> Dict[str, "ibm_backend.IBMBackend"]:
        """Gets the backends for the hub/group/project, if not loaded.

        Returns:
            Dict[str, IBMBackend]: the backends
        """
        if not self._backends:
            self._backends = self._discover_remote_backends()
        return self._backends

    @backends.setter
    def backends(self, value: Dict[str, "ibm_backend.IBMBackend"]) -> None:
        """Sets the value for the hub/group/project's backends.

        Args:
            value: the backends
        """
        self._backends = value

    def _discover_remote_backends(
        self, timeout: Optional[float] = None
    ) -> Dict[str, "ibm_backend.IBMBackend"]:
        """Return the remote backends available for this hub/group/project.

        Args:
            timeout: Maximum number of seconds to wait for the discovery of
                remote backends.

        Returns:
            A dict of the remote backend instances, keyed by backend name.
        """
        ret = OrderedDict()  # type: ignore[var-annotated]
        configs_list = self._api_client.list_backends(timeout=timeout)
        for raw_config in configs_list:
            # Make sure the raw_config is of proper type
            if not isinstance(raw_config, dict):
                logger.warning(
                    "An error occurred when retrieving backend "
                    "information. Some backends might not be available."
                )
                continue
            try:
                decode_backend_configuration(raw_config)
                try:
                    config = PulseBackendConfiguration.from_dict(raw_config)
                except (KeyError, TypeError):
                    config = QasmBackendConfiguration.from_dict(raw_config)
                backend_cls = (
                    ibm_backend.IBMSimulator
                    if config.simulator
                    else ibm_backend.IBMBackend
                )
                ret[config.backend_name] = backend_cls(
                    configuration=config,
                    service=self._service,
                    credentials=self.credentials,
                    api_client=self._api_client,
                )
            except Exception:  # pylint: disable=broad-except
                logger.warning(
                    'Remote backend "%s" for provider %s could not be instantiated due to an '
                    "invalid config: %s",
                    raw_config.get("backend_name", raw_config.get("name", "unknown")),
                    repr(self),
                    traceback.format_exc(),
                )
        return ret

    def get_backend(self, name: str) -> Optional[Backend]:
        """Get backend by name."""
        return self._backends.get(name, None)

    def has_service(self, name: str) -> bool:
        """Check if hgp has service by name."""
        if name not in self._service_urls:
            raise IBMInputValueError(f"Unknown service {name} specified.")
        return self._service_urls[name] is not None

    def __repr__(self) -> str:
        credentials_info = "hub='{}', group='{}', project='{}'".format(
            self.credentials.hub, self.credentials.group, self.credentials.project
        )
        return "<{}({})>".format(self.__class__.__name__, credentials_info)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HubGroupProject):
            return False
        return self.credentials == other.credentials
