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

from numbers import Real
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, field_validator

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import ValidationInfo

PRIMITIVES_CONFIG = ConfigDict(validate_assignment=True, extra="forbid")
"""Custom ``ConfigDict`` for pydantic dataclasses.

These config settings ensure we get validation on attribute mutation, not just at construction
time, and also that we get a validation error if someone spells an attribute name wrong.
"""


def make_constraint_validator(
    *field_names: str,
    ge: Real | None = None,
    gt: Real | None = None,
    le: Real | None = None,
    lt: Real | None = None,
) -> Callable:
    """Make a field validator that performs the give constraint if the value is numeric.

    This differs to the one built-in to ``pydantic.Field`` in that it ignores non-Real types,
    which lets us apply this to fields with annotations like ``int | Literal["auto"]``.

    Args:
        field_names: The field names to check.
        ge: A number the value must be greater than or equal to.
        gt: A number the value must be strictly greater than.
        le: A number the value must be less than or equal to.
        lt: A number the value must be strictly less than.

    Returns:
        A new field validator.
    """

    @field_validator(*field_names, mode="before")  # type: ignore[misc]
    @classmethod
    def validator(cls: Any, value: Any, validation_info: ValidationInfo) -> Any:
        if isinstance(value, Real):
            if ge is not None and (value < ge):
                raise ValueError(
                    f"{cls.__name__}.{validation_info.field_name} must be >={ge}, but is =={value}."
                )
            if gt is not None and (value <= gt):
                raise ValueError(
                    f"{cls.__name__}.{validation_info.field_name} must be >{gt}, but is =={value}."
                )
            if le is not None and (value > le):
                raise ValueError(
                    f"{cls.__name__}.{validation_info.field_name} must be <={le}, but is =={value}."
                )
            if lt is not None and (value >= lt):
                raise ValueError(
                    f"{cls.__name__}.{validation_info.field_name} must be <{lt}, but is =={value}."
                )
        return value

    return validator
