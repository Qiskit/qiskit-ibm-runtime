# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Fake AccountClient."""

from datetime import datetime as python_datetime
from typing import List, Dict, Any, Optional

from qiskit.providers.fake_provider import FakeLima


class FakeApiBackend:
    """Fake backend."""

    def __init__(self, config_update=None, status_update=None):
        fake_backend = FakeLima()
        self.properties = fake_backend.properties().to_dict()
        self.defaults = fake_backend.defaults().to_dict()

        self.configuration = fake_backend.configuration().to_dict()
        self.configuration["online_date"] = python_datetime.now().isoformat()
        if config_update:
            self.configuration.update(**config_update)
        self.name = self.configuration["backend_name"]

        self.status = fake_backend.status().to_dict()
        if status_update:
            self.status.update(**status_update)


class BaseFakeAccountClient:
    """Base class for faking the AccountClient."""

    def __init__(
        self,
        hgp: Optional[str] = None,
        num_backends: int = 2,
        specs: List[Dict] = None,
    ):
        """Initialize a fake account client.

        Args:
            hgp: Hub/group/project to use.
            num_backends: Number of backends. Ignored if ``specs`` is specified.
            specs: Backend specs. This is a dictionary of overwritten backend
                configuration / status. For example::

                    specs = [ {"configuration": {"backend_name": "backend1"},
                                                 "status": {"operational": False}}
                    ]
        """
        self._hgp = hgp
        self._fake_backend = FakeLima()
        self._backends = []
        if not specs:
            specs = [{}] * num_backends

        for idx, backend_spec in enumerate(specs):
            config = backend_spec.get("configuration", {})
            status = backend_spec.get("status", {})
            if "backend_name" not in config:
                config["backend_name"] = f"backend{idx}"
            self._backends.append(FakeApiBackend(config, status))

    def list_backends(self) -> List[Dict[str, Any]]:
        """Return backends available for this provider."""
        # pylint: disable=unused-argument
        return [back.configuration.copy() for back in self._backends]

    def backend_status(self, backend_name: str) -> Dict[str, Any]:
        """Return the status of the backend."""
        for back in self._backends:
            if back.name == backend_name:
                return back.status.copy()
        raise ValueError(f"Backend {backend_name} not found")

    def backend_properties(
        self, backend_name: str, datetime: Optional[python_datetime] = None
    ) -> Dict[str, Any]:
        """Return the properties of the backend."""
        # pylint: disable=unused-argument
        for back in self._backends:
            if back.name == backend_name:
                return back.properties.copy()
        raise ValueError(f"Backend {backend_name} not found")

    def backend_pulse_defaults(self, backend_name: str) -> Dict:
        """Return the pulse defaults of the backend."""
        for back in self._backends:
            if back.name == backend_name:
                return back.defaults.copy()
        raise ValueError(f"Backend {backend_name} not found")

    # Test-only methods.

    @property
    def backend_names(self):
        """Return names of the backends."""
        return [back.name for back in self._backends]

    @property
    def hgp(self):
        """Return hub/group/project."""
        return self._hgp
