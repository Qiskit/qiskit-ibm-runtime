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

import copy
import functools
from dataclasses import asdict, is_dataclass
from numbers import Real
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import ConfigDict, field_validator
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import ValidationInfo

    from ..options.options import BaseOptions


def remove_dict_unset_values(in_dict: dict) -> None:
    """Remove Unset values."""
    for key, val in list(in_dict.items()):
        if isinstance(val, UnsetType):
            del in_dict[key]
        elif isinstance(val, dict):
            remove_dict_unset_values(val)


def remove_empty_dict(in_dict: dict) -> None:
    """Remove empty dictionaries."""
    for key, val in list(in_dict.items()):
        if isinstance(val, dict):
            if val:
                remove_empty_dict(val)
            if not val:
                del in_dict[key]


def merge_options_v2(old_options: dict | BaseOptions, new_options: dict | None = None) -> dict:
    """Merge current options with the new ones for V2 primitives.

    This function does not attempt to merge values of the same keys from different nesting levels.

    Args:
        old_options: Old options to merge.
        new_options: New options to merge.

    Returns:
        Merged dictionary.

    Raises:
        TypeError: if input type is invalid.
    """

    def _update_options(old: dict, new: dict) -> None:
        if not new:
            return

        # Update values of existing keys
        for key, val in old.items():
            if key in new.keys():
                if isinstance(val, dict):
                    _update_options(val, new.pop(key))
                else:
                    old[key] = new.pop(key)

        # Add new keys.
        for key in list(new.keys()):
            old[key] = new.pop(key)

    if is_dataclass(old_options):
        combined = asdict(old_options)
    elif isinstance(old_options, dict):
        combined = copy.deepcopy(old_options)
    else:
        raise TypeError("'old_options' can only be a dictionary or dataclass.")

    if not new_options:
        return combined
    new_options_copy = copy.deepcopy(new_options)

    _update_options(combined, new_options_copy)

    return combined


def skip_unset_validation(func: Callable) -> Callable:
    """Decorator used to skip unset value."""

    @functools.wraps(func)
    def wrapper(cls: Any, val: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(val, UnsetType):
            return val
        return func(cls, val, *args, **kwargs)

    return wrapper


class Dict:
    """Fake Dict type.

    This class is used to show dictionary as an acceptable type in docs without
    attaching all the dictionary attributes in Jupyter's auto-complete.
    """

    pass


class UnsetType:
    """Class used to represent an unset field."""

    _instance: ClassVar[UnsetType | None] = None

    def __repr__(self) -> str:
        return "Unset"

    def __new__(cls) -> UnsetType:
        """Construct a ``UnsetType`` instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False


Unset = UnsetType()


primitive_dataclass = dataclass(
    config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=True, extra="forbid")
)


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
    @skip_unset_validation
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
