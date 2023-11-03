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

"""Utility functions for options."""

from typing import Optional, Union, Callable
import functools
import copy
from dataclasses import is_dataclass, asdict

from ..ibm_backend import IBMBackend


def set_default_error_levels(
    options: dict,
    backend: IBMBackend,
    default_optimization_level: int,
    default_resilience_level: int,
) -> dict:
    """Set default resilience and optimization levels.

    Args:
        options: user passed in options.
        backend: backend the job will run on.
        default_optimization_level: the default optimization level from the options class
        default_resilience_level: the default resilience level from the options class

    Returns:
        options with correct error level defaults.
    """
    if options.get("optimization_level") is None:
        if (
            backend.configuration().simulator
            and options.get("simulator", {}).get("noise_model") is None
        ):
            options["optimization_level"] = 1
        else:
            options["optimization_level"] = default_optimization_level

    if options.get("resilience_level") is None:
        if (
            backend.configuration().simulator
            and options.get("simulator", {}).get("noise_model") is None
        ):
            options["resilience_level"] = 0
        else:
            options["resilience_level"] = default_resilience_level
    return options


def _remove_dict_unset_values(in_dict: dict) -> None:
    """Remove Unset values."""
    for key, val in list(in_dict.items()):
        if isinstance(val, UnsetType):
            del in_dict[key]
        elif isinstance(val, dict):
            _remove_dict_unset_values(val)


def _to_obj(cls_, data):  # type: ignore
    if data is None:
        return cls_()
    if isinstance(data, cls_):
        return data
    if isinstance(data, dict):
        return cls_(**data)
    raise TypeError(
        f"{data} has an unspported type {type(data)}. It can only be {cls_} or a dictionary."
    )


def merge_options(
    old_options: Union[dict, "BaseOptions"], new_options: Optional[dict] = None
) -> dict:
    """Merge current options with the new ones.

    Args:
        new_options: New options to merge.

    Returns:
        Merged dictionary.
    """

    def _update_options(old: dict, new: dict, matched: Optional[dict] = None) -> None:
        if not new and not matched:
            return
        matched = matched or {}

        for key, val in old.items():
            if isinstance(val, dict):
                matched = new.pop(key, {})
                _update_options(val, new, matched)
            elif key in new.keys():
                old[key] = new.pop(key)
            elif key in matched.keys():
                old[key] = matched.pop(key)

        # Add new keys.
        for key, val in matched.items():
            old[key] = val

    combined = asdict(old_options) if is_dataclass(old_options) else copy.deepcopy(old_options)
    if not new_options:
        return combined
    new_options_copy = copy.deepcopy(new_options)

    # First update values of the same key.
    _update_options(combined, new_options_copy)

    # Add new keys.
    combined.update(new_options_copy)

    return combined


def skip_unset_validation(func: Callable) -> Callable:
    """Decorator used to skip unset value"""

    @functools.wraps(func)
    def wrapper(cls, val, *args, **kwargs) -> Callable:
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

    def __repr__(self) -> str:
        return "Unset"

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance


Unset: UnsetType = UnsetType()
