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

"""Base class for options models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Iterable


class BaseOptionsModel(BaseModel):
    """Base class for options models."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    """Custom ``ConfigDict`` for pydantic dataclasses.

    These config settings ensure we get validation on attribute mutation, not just at construction
    time, and also that we get a validation error if someone spells an attribute name wrong.
    """

    def __dir__(self) -> Iterable[str]:
        """Return the list of public attributes.

        Custom implementation that returns only the attributes that are field names, in order to
        prevent auto-completing in interactive shells to display all ``BaseModel`` methods.
        """
        return list(self.__class__.model_fields.keys())

    def update(self, **kwargs: Any) -> None:
        """Update the options."""
        for key, value in kwargs.items():
            current_field_value = getattr(self, key, None)
            if isinstance(current_field_value, BaseOptionsModel):
                # If the field is a nested model, recursively update.
                current_field_value.update(**value)
            else:
                setattr(self, key, value)
