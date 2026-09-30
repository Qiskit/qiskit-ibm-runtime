# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Standalone assertion helpers for qiskit-ibm-runtime test cases."""

from __future__ import annotations

import inspect
import os
import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


def assert_dict_partially_equal(a: dict, b: dict) -> None:
    """Assert that all keys in ``b`` are in ``a`` and have the same values."""

    def _dict_partially_equal(dict1: dict, dict2: dict) -> bool:
        """Determine whether all keys in dict2 are in dict1 and have same values."""
        for key, val in dict2.items():
            if isinstance(val, dict):
                if not _dict_partially_equal(dict1.get(key, {}), val):
                    return False
            elif key not in dict1 or val != dict1[key]:
                return False

        return True

    if not _dict_partially_equal(a, b):
        raise AssertionError(f"Dicts are not partially equal: {a}, {b}")


def assert_dict_flat_partially_equal(a: dict, b: dict) -> None:
    """Assert that (when flattened) all keys in ``b`` are in ``a`` and have the same values."""

    def _flat_dict(in_dict: dict, out_dict: dict) -> None:
        """Flat the dictionaries, and compare.

        Flat the dictionaries, then determine whether all keys in dict2 are in dict1 and have the
        same values.
        """
        for key_, val_ in in_dict.items():
            if isinstance(val_, dict):
                _flat_dict(val_, out_dict)
            else:
                out_dict[key_] = val_

    flat_dict1: dict = {}
    flat_dict2: dict = {}
    _flat_dict(a, flat_dict1)
    _flat_dict(b, flat_dict2)

    for key, val in flat_dict2.items():
        if key not in flat_dict1 or flat_dict1[key] != val:
            raise AssertionError(f"Dicts are not partially equal when flattened: {a}, {b}")


def assert_dict_keys_equal(a: dict, b: dict, exclude_keys: list | None = None) -> None:
    """Assert recursively that ``a`` and ``b`` have the same keys, optionally excluding keys."""

    def _dict_keys_equal(dict1: dict, dict2: dict, exclude_keys: list | None = None) -> bool:
        """Recursively determine whether the dictionaries have the same keys.

        Args:
            dict1: First dictionary.
            dict2: Second dictionary.
            exclude_keys: A list of keys in dictionary 1 to be excluded.

        Returns:
            Whether the two dictionaries have the same keys.
        """
        exclude_keys = exclude_keys or []
        for key, val in dict1.items():
            if key in exclude_keys:
                continue
            if key not in dict2:
                return False
            if isinstance(val, dict):
                if not _dict_keys_equal(val, dict2[key]):
                    return False

        return True

    if not _dict_keys_equal(a, b, exclude_keys):
        raise AssertionError(f"Dicts don't have the same keys: {a}, {b}")


@contextmanager
def assert_warns_strict(
    warning: type[Warning],
    msg: str,
    num_appearances: int,
    attributed_to_caller: bool = True,
) -> Iterator[None]:
    """Assert that a warning matching the category and message appears a set number of times.

    Args:
        warning: The warning category to match.
        msg: A substring that must appear in the warning message.
        num_appearances: The exact number of matching warnings expected.
        attributed_to_caller: When ``True`` (default), also assert that each matching warning is
            blamed on this function's caller -- the frame that opened the ``with`` block. This
            verifies the emitting call sets ``stacklevel`` so the warning points at the user's own
            code, which is what makes it visible in scripts and Jupyter notebooks. Assumes the
            warning-emitting call is made directly inside the ``with`` block; set to ``False`` when
            the call is wrapped in a helper defined in another file.
    """
    # The caller is the frame that opened the ``with`` block: this generator frame (0),
    # contextlib's ``_GeneratorContextManager`` wrapper (1), then the caller (2).
    caller = inspect.stack()[2]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", warning)
        yield

    matching_warnings = [
        w for w in caught if issubclass(w.category, warning) and msg in str(w.message)
    ]
    all_warnings = [
        f"{w.category.__name__}: {w.message}" for w in caught if issubclass(w.category, Warning)
    ]
    assert len(matching_warnings) == num_appearances, (
        f"Expected {num_appearances} {warning.__name__} warnings containing "
        f"{msg!r}, found {len(matching_warnings)}. All warnings: {all_warnings}"
    )

    if attributed_to_caller:
        caller_file = os.path.abspath(caller.filename)
        for w in matching_warnings:
            assert os.path.abspath(w.filename) == caller_file, (
                f"Warning {msg!r} was blamed on {w.filename}:{w.lineno}, not the caller's "
                f"frame ({caller.filename}:{caller.lineno}). Its stacklevel must point at "
                f"the user's code -- past any qiskit_ibm_runtime or pydantic internals -- "
                f"so the warning is visible in scripts and Jupyter notebooks."
            )
