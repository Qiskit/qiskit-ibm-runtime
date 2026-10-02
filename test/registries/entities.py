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

"""Entities to be used with registries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeAlias

from qiskit_ibm_runtime.fake_provider import FakeLimaV2

if TYPE_CHECKING:
    from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2


PricingType: TypeAlias = Literal["free", "trial", "paygo", "paid", "subscription", "unknown"]
"""Pricing types for an instance."""

JobStatus: TypeAlias = Literal["queued", "running", "completed", "cancelled", "failed"]
"""Possible job statuses."""

DEFAULT_BACKED_CONFIGURATION = FakeLimaV2()._load_json(FakeLimaV2.conf_filename)
"""Default configuration for registry backends, cached and based on FakeLima."""

DEFAULT_BACKED_PROPERTIES = FakeLimaV2()._load_json(FakeLimaV2.props_filename)
"""Default properties for registry backends, cached and based on FakeLima."""


@dataclass
class Instance:
    """Registry representation of an instance.

    The following fields will be initialized if set to their default value:
    * `crn`
    * `usage`
    """

    name: str
    """Name of the instance."""

    crn: str = ""
    """CRN of the instance. If not set, will be automatically initialized."""

    allocations: int = 42
    """Allocations of the instance."""

    pricing_type: PricingType = "free"
    """Pricing type of the instance."""

    usage: dict | None = None
    """Instance usage dictionary."""

    tags: list = field(default_factory=list)
    """Instance tags."""

    def __post_init__(self) -> None:
        if not self.crn:
            self.crn = f"crn:v1:bluemix:public:quantum-computing:my-region:{self.name}/...:...::"

        if self.usage is None:
            self.usage = {
                "instance_id": self.crn,
                "usage_consumed_seconds": 12,
                "usage_limit_seconds": 60,
                "usage_allocation_seconds": 120,
                "usage_limit_reached": False,
            }


@dataclass
class Backend:
    """Registry representation of a backend.

    The following fields will be initialized if set to their default value:
    * `configuration`: set based on `FakeLimaV2`.
    * `properties`: set based on `FakeLimaV2`.
    """

    name: str
    """Name of the backend."""

    configuration: dict = field(default_factory=dict)
    """Configuration of the backend."""

    properties: dict = field(default_factory=dict)
    """Properties of the backend."""

    status: Literal["online", "paused", "offline"] = "online"
    """Status of the backend."""

    queue_length: int = 0
    """Lenght of the queue for this backend."""

    calibrations: dict[str, dict] = field(default_factory=dict)
    """Configuration overrides keyed by calibration id."""

    is_mock: bool = False
    """Whether the backend is a mock device."""

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
        calibrations: dict[str, dict] | None = None,
        is_mock: bool = False,
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
            calibrations=calibrations or {},
            is_mock=is_mock,
        )


@dataclass
class Job:
    """Registry representation of a job.

    The following fields will be initialized if set to their default value:
    * `usage`
    """

    id: str
    """Job id."""

    backend_name: str
    """Backend name."""

    program: Literal["sampler", "estimator", "executor"] = "sampler"

    status: JobStatus = "completed"
    """Job status."""

    raw_details: str | None = None
    """Response for the job details."""

    raw_results: str | None = None
    """Response for the job results."""

    usage: dict | None = None
    """Job usage dictionary."""

    statuses: list[JobStatus] = field(default_factory=lambda: ["completed"])
    """States that a job goes through."""

    statuses_reason: dict[JobStatus, tuple[int, str]] = field(default_factory=dict)
    """Reason code and reason message for each job status."""

    def __post_init__(self) -> None:
        if self.usage is None:
            self.usage = {
                "qpu_charge_time_seconds": 0 if self.status != "completed" else 20,
                "status": "pending" if self.status in ("queued", "running") else "completed",
            }

    def advance_status(self) -> None:
        """Set `self.status` to the next one."""
        current_index = self.statuses.index(self.status)
        next_index = min(len(self.statuses) - 1, current_index + 1)
        self.status = self.statuses[next_index]


@dataclass
class Session:
    """Registry representation of a session."""

    id: str
    """Session id."""

    backend_name: str
    """Backend name."""

    mode: Literal["batch", "dedicated"] = "dedicated"
    """Session mode."""

    timestamps: list[dict[str, str]] | None = None
    """Session state transitions, as returned by the API."""
