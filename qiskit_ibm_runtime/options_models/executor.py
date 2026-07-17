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

from .base import BaseOptionsModel
from .environment import EnvironmentOptions
from .execution import ExecutionOptions


class ExecutorOptions(BaseOptionsModel):
    """Options for the executor."""

    environment: EnvironmentOptions = EnvironmentOptions()
    """Options related to the execution environment."""

    execution: ExecutionOptions = ExecutionOptions()
    """Low-level execution options."""

    experimental: dict = {}
    """Experimental options that are passed to the executor."""
