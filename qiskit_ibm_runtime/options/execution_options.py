# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Execution options."""

from typing import Union

from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic import ConfigDict, model_validator, field_validator, ValidationInfo

from .utils import Unset, UnsetType, skip_unset_validation


@pydantic_dataclass(
    config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=True, extra="forbid")
)
class ExecutionOptionsV2:
    """Execution options.

    Args:
        shots: Number of repetitions of each circuit, for sampling.

        init_qubits: Whether to reset the qubits to the ground state for each shot.
            Default: ``True``.

        samples: The number of samples of each measurement circuit to run. This
            is used when twirling or resilience levels 1, 2, 3. If None it will
            be calculated automatically based on the ``shots`` and
            ``shots_per_sample`` (if specified).
            Default: Unset

        shots_per_sample: The number of shots per sample of each measurement
            circuit to run. This is used when twirling or resilience levels 1, 2, 3.
            If None it will be calculated automatically based on the ``shots`` and
            ``samples`` (if specified).
            Default: Unset

        interleave_samples: If True interleave samples from different measurement
            circuits when running. If False run all samples from each measurement
            circuit in order.
            Default: False
    """

    shots: Union[UnsetType, int] = Unset
    init_qubits: bool = True
    samples: Union[UnsetType, int] = Unset
    shots_per_sample: Union[UnsetType, int] = Unset
    interleave_samples: Union[UnsetType, bool] = Unset

    @field_validator("shots", "samples", "shots_per_sample")
    @classmethod
    @skip_unset_validation
    def _validate_positive_integer(cls, fld: int, info: ValidationInfo) -> int:
        """Validate zne_stderr_threshold."""
        if fld < 1:
            raise ValueError(f"{info.field_name} must be >= 1")
        return fld

    @model_validator(mode="after")
    def _validate_options(self) -> "ExecutionOptionsV2":
        """Validate the model."""
        if (
            all(
                not isinstance(fld, UnsetType)
                for fld in [self.shots, self.samples, self.shots_per_sample]
            )
            and self.shots != self.samples * self.shots_per_sample  # type: ignore[operator]
        ):
            raise ValueError(
                f"Shots ({self.shots}) != "
                f"samples ({self.samples}) * shots_per_sample ({self.shots_per_sample})"
            )
        return self


@pydantic_dataclass(
    config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=True, extra="forbid")
)
class ExecutionOptionsV1:
    """Execution options.

    Args:
        shots: Number of repetitions of each circuit, for sampling. Default: 4000.

        init_qubits: Whether to reset the qubits to the ground state for each shot.
            Default: ``True``.
    """

    shots: int = 4000
    init_qubits: bool = True
