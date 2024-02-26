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

"""Classes for FakeApiBackends"""
from typing import Optional
from datetime import datetime as python_datetime
from dataclasses import dataclass

from qiskit_ibm_runtime.fake_provider import FakeLima


@dataclass
class FakeApiBackendSpecs:
    """FakeApiBackend specs."""

    backend_name: str
    configuration: dict = None
    """Backend configuration to overwrite."""
    status: dict = None
    """Backend status to overwrite."""
    hgps: list = None
    """HGPs that can access this backend. None if all can."""


class FakeApiBackend:
    """Fake backend."""

    def __init__(self, specs: Optional[FakeApiBackendSpecs] = None):
        fake_backend = FakeLima()
        self.properties = fake_backend.properties().to_dict()
        self.defaults = fake_backend.defaults().to_dict()

        self.configuration = fake_backend.configuration().to_dict()
        self.configuration["online_date"] = python_datetime.now().isoformat()
        self.configuration["backend_name"] = specs.backend_name
        if specs.configuration:
            self.configuration.update(**specs.configuration)
        self.name = self.configuration["backend_name"]

        self.status = fake_backend.status().to_dict()
        if specs.status:
            self.status.update(**specs.status)

        self.hgps = specs.hgps

    def has_access(self, hgp):
        """Check if hgp is accessible"""
        if not self.hgps:
            return True
        return hgp in self.hgps
