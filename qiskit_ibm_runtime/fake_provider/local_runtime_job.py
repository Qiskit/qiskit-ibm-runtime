# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit runtime local mode job class."""

from typing import Any, Dict, Literal
from datetime import datetime

from qiskit.primitives.primitive_job import PrimitiveJob
from qiskit_ibm_runtime.models import BackendProperties
from .fake_backend import FakeBackendV2  # pylint: disable=cyclic-import


class LocalRuntimeJob(PrimitiveJob):
    """Job class for qiskit-ibm-runtime's local mode."""

    def __init__(  # type: ignore[no-untyped-def]
        self,
        future,
        backend: FakeBackendV2,
        primitive: Literal["sampler", "estimator"],
        *args,
        **kwargs,
    ) -> None:
        """LocalRuntimeJob constructor.

        Args:
            future: Thread executor the job is run on.
            backend: The backend to run the primitive on.
        """
        super().__init__(*args, **kwargs)
        self._future = future
        self._backend = backend
        self._primitive = primitive
        self._created = datetime.now()
        self._running = datetime.now()
        self._finished = datetime.now()

    def metrics(self) -> Dict[str, Any]:
        """Return job metrics.

        Returns:
            A dictionary with job metrics including but not limited to the following:

            * ``timestamps``: Timestamps of when the job was created, started running, and finished.
            * ``usage``: Details regarding job usage, the measurement of the amount of
                time the QPU is locked for your workload.
        """
        return {
            "bss": {"seconds": 0},
            "usage": {"quantum_seconds": 0, "seconds": 0},
            "timestamps": {
                "created": self._created,
                "running": self._running,
                "finished": self._finished,
            },
        }

    def backend(self) -> FakeBackendV2:
        """Return the backend where this job was executed."""
        return self._backend

    def useage(self) -> float:
        """Return job usage in seconds."""
        return 0

    def properties(self) -> BackendProperties:
        """Return the backend properties for this job"""
        return self._backend.properties()

    @property
    def creation_date(self) -> datetime:
        """Job creation date in local time."""
        return self._created

    @property
    def primitive_id(self) -> str:
        """Primitive name."""
        return self._primitive
