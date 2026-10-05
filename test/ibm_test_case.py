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

"""Custom TestCases for IBM Provider."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import TestCase  # noqa: TID251 -- IBMTestCase legitimatelly inherits from it.

from .asserts import (
    assert_dict_flat_partially_equal,
    assert_dict_keys_equal,
    assert_dict_partially_equal,
    assert_warns_strict,
)

if TYPE_CHECKING:
    from contextlib import AbstractContextManager


class IBMTestCase(TestCase):
    """Custom TestCase for use with qiskit-ibm-runtime."""

    def assertDictPartiallyEqual(self, a: dict, b: dict) -> None:
        """Assert that all keys in ``b`` are in ``a`` and have the same values."""
        assert_dict_partially_equal(a, b)

    def assertDictFlatPartiallyEqual(self, a: dict, b: dict) -> None:
        """Assert that (when flattened) all keys in ``b`` are in ``a`` and have the same values."""
        assert_dict_flat_partially_equal(a, b)

    def assertDictKeysEqual(self, a: dict, b: dict, exclude_keys: list | None = None) -> None:
        """Assert recursively that ``a`` and ``b`` have the same keys, optionally excluding keys."""
        assert_dict_keys_equal(a, b, exclude_keys)

    def assertWarnsStrict(
        self,
        warning: type[Warning],
        msg: str,
        num_appearances: int,
        attributed_to_caller: bool = True,
    ) -> AbstractContextManager[None]:
        """Assert that a warning matching the category and message appears a set number of times.

        Args:
            warning: The warning category to match.
            msg: A substring that must appear in the warning message.
            num_appearances: The exact number of matching warnings expected.
            attributed_to_caller: When ``True`` (default), also assert that each matching
                warning is blamed on this method's caller -- the frame that opened the
                ``with`` block. This verifies the emitting call sets ``stacklevel`` so the warning
                points at the user's own code, which is what makes it visible in scripts and
                Jupyter notebooks. Assumes the warning-emitting call is made directly inside the
                ``with`` block; set to ``False`` when the call is wrapped in a helper defined in
                another file.
        """
        return assert_warns_strict(warning, msg, num_appearances, attributed_to_caller)
