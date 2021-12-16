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

from typing import List, Dict, Any, Union
from datetime import datetime

from qiskit.test.mock.backends import FakeLima


class BaseFakeAccountClient:
    """Base class for faking the AccountClient."""

    def __init__(self, backend_names: Union[int, List[str]] = 2):
        """Initialize a fake account client.

        Args:
            backend_names: Names of the backends. This can be either the number of
                randomly generated names or actual names.
        """
        self._fake_backend = FakeLima()
        self._backend_names = []
        if isinstance(backend_names, int):
            for idx in range(backend_names):
                self._backend_names.append(f"backend{idx}")
        else:
            self._backend_names = backend_names.copy()

    def list_backends(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Return backends available for this provider."""
        backends = []
        for name in self._backend_names:
            config_dict = self._fake_backend.configuration().to_dict()
            config_dict["online_date"] = datetime.now().isoformat()
            config_dict["backend_name"] = name
            backends.append(config_dict)

        return backends

    def backend_status(self, backend_name: str) -> Dict[str, Any]:
        """Return the status of the backend.

        Args:
            backend_name: The name of the backend.

        Returns:
            Backend status.
        """
        return {"backend_name": backend_name, "backend_version": "1.0", "operational": True,
                "pending_jobs": 0, "status_msg": "active"}

    def backend_properties(self, *args, **kwargs) -> Dict[str, Any]:
        """Return the properties of the backend."""
        return self._fake_backend.properties()

    def backend_pulse_defaults(self, *args, **kwargs) -> Dict:
        """Return the pulse defaults of the backend."""
        return self._fake_backend.defaults()

    # Test-only methods.

    @property
    def backend_names(self):
        """Return names of the backends."""
        return self._backend_names
