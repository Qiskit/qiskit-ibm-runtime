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

"""Serialization utility functions for runtime testing."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from qiskit_ibm_runtime.decoders.result_decoder import ResultDecoder

if TYPE_CHECKING:
    from typing_extensions import Self


def get_complex_types() -> dict:
    """Return a dictionary with values of more complicated types."""
    return {
        "string": "foo",
        "float": 1.5,
        "complex": 2 + 3j,
        "serializable_class": SerializableClass("foo"),
    }


class SerializableClass:
    """Custom class with serialization methods."""

    def __init__(self, value: Any):
        self.value = value

    def to_json(self) -> str:
        """To JSON serializable."""
        return json.dumps({"value": self.value})

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """From JSON serializable."""
        return cls(**json.loads(json_str))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.value == self.from_json(other).value
        return self.value == other.value


class SerializableClassDecoder(ResultDecoder):
    """Decoder used for decode SerializableClass in job result."""

    @classmethod
    def decode(cls, data):
        """Decode input data."""
        decoded = super().decode(data)
        if "serializable_class" in decoded:
            decoded["serializable_class"] = SerializableClass.from_json(
                decoded["serializable_class"]
            )
        return decoded
