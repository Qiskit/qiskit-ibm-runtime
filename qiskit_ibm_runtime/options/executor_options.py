# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Executor options."""

from __future__ import annotations


from pydantic.dataclasses import dataclass
from pydantic import Field

from .execution_options import ExecutionOptions
from .environment_options import EnvironmentOptionsV2
from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class ExecutorOptions:
    """Options for the executor."""

    environment: EnvironmentOptionsV2 = Field(default_factory=EnvironmentOptionsV2)
    """Options related to the execution environment."""

    execution: ExecutionOptions = Field(default_factory=ExecutionOptions)
    """Low-level execution options."""

    experimental: dict = Field(default_factory=dict)
    """Experimental options that are passed to the executor."""
