# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utility functions for options."""

from __future__ import annotations

from pydantic import ConfigDict


PRIMITIVES_CONFIG = ConfigDict(validate_assignment=True, extra="forbid")
"""Custom ``ConfigDict`` for pydantic dataclasses.

These config settings ensure we get validation on attribute mutation, not just at construction
time, and also that we get a validation error if someone spells an attribute name wrong.
"""
