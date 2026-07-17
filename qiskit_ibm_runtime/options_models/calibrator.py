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

from pydantic import Field
from pydantic.dataclasses import dataclass

from .environment import EnvironmentOptions
from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class CalibratorOptions:
    """Options for the calibrator."""

    environment: EnvironmentOptions = Field(default_factory=EnvironmentOptions)
    """Options related to the execution environment."""

    experimental: dict = Field(default_factory=dict)
    """Experimental options that are passed to the executor."""
