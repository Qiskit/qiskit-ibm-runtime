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

"""Tests for the BaseOptionsModel class."""

from dataclasses import asdict

from pydantic import ValidationError

from qiskit_ibm_runtime.options_models.base import BaseOptionsModel

from ...ibm_test_case import IBMTestCase


class Nested(BaseOptionsModel):
    """Nested options model, for testing."""

    b: str = "b"
    n: int | None = None


class Options(BaseOptionsModel):
    """Options model for testing."""

    a: str = "a"
    nested: Nested = Nested()


class TestBaseOptionsModel(IBMTestCase):
    """Tests for the BaseOptionsModel class."""

    def test_update(self):
        """Test the `update()` method."""
        options = Options()
        options_dict = options.model_dump()

        # Updating top-level field.
        options.update(**{"a": "new_a"})
        options_dict.update(**{"a": "new_a"})
        self.assertEqual(options_dict, options.model_dump())

        # Updating nested fields.
        options.update(**{"nested": {"n": 42}})
        options_dict["nested"].update(**{"n": 42})
        self.assertEqual(options_dict, options.model_dump())

        # Should fail when trying to update a non-existing field.
        with self.assertRaises(ValidationError):
            options.update(**{"z": None})

        # Should fail when trying to update a field with an invalid value.
        with self.assertRaises(ValidationError):
            options.update(**{"a": None})

    def test_asdict(self):
        """Test the ability to use `dataclass.asdict()` in an OptionsModel."""
        options = Options()
        self.assertEqual(asdict(options), options.model_dump())
