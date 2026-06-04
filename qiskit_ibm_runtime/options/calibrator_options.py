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

"""Calibrator options."""

from __future__ import annotations

from typing import Annotated

from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(validate_assignment=True, extra="forbid"))
class CalibratorOptions:
    """Options for the calibrator."""

    image: (
        Annotated[
            str,
            Field(
                pattern="[a-zA-Z0-9]+([/.\\-_][a-zA-Z0-9]+)*:[a-zA-Z0-9]+([.\\-_][a-zA-Z0-9]+)*$",
            ),
        ]
        | None
    ) = None
    """Runtime image used for this job."""
