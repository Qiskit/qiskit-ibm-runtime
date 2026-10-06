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

"""Test deserializing server data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dateutil.parser

from qiskit_ibm_runtime.api.exceptions import RequestsApiError

from ..decorators import production_only
from .case import IBMIntegrationTestCase

if TYPE_CHECKING:
    from collections.abc import Iterator


def assert_data_not_encoded(
    data: dict, good_keys: tuple[str, ...], good_key_prefixes: tuple[str, ...] = ()
) -> None:
    """Assert that no field of `data` holds a JSON-serialized object.

    Args:
        data: Data to validate.
        good_keys: Keys known to hold a value that looks serialized but is legitimate.
        good_key_prefixes: Prefixes of keys known to hold a value that looks serialized
            but is legitimate.
    """
    suspects = {
        key
        for key in _encoded_looking_keys(data)
        if key not in good_keys and not key.startswith(good_key_prefixes)
    }
    assert not suspects


def _encoded_looking_keys(data: Any, path: str = "") -> Iterator[str]:
    """Yield the path of every field of `data` whose value looks JSON-serialized.

    Args:
        data: Data to traverse recursively.
        path: Dot-separated path of the field currently being traversed.
    """
    if _looks_encoded(data):
        yield path

    if isinstance(data, list):
        for item in data:
            yield from _encoded_looking_keys(item, path)
    elif isinstance(data, dict):
        for key, value in data.items():
            yield from _encoded_looking_keys(value, f"{path}.{key}" if path else str(key))


def _looks_encoded(data: Any) -> bool:
    """Check whether `data` could be a serialized complex number or datetime."""
    if isinstance(data, list):
        return len(data) == 2 and all(isinstance(item, (float, int)) for item in data)
    if isinstance(data, str):
        try:
            dateutil.parser.parse(data)
            return True
        except ValueError:
            return False
    return False


class TestSerialization(IBMIntegrationTestCase):
    """Test data serialization."""

    @production_only
    def test_backend_configuration(self):
        """Test deserializing backend configuration."""
        service = self.service
        instance = None
        backends = service.backends(operational=True, simulator=False, instance=instance)

        # Known keys that look like a serialized complex number.
        good_keys = (
            "coupling_map",
            "qubit_lo_range",
            "meas_lo_range",
            "rep_times",
            "gates.coupling_map",
            "meas_levels",
            "qubit_channel_mapping",
            "backend_version",
            "rep_delay_range",
            "processor_type.revision",
            "coords",
        )
        good_keys_prefixes = ("channels",)

        for i, backend in enumerate(backends):
            with self.subTest(msg=f"backend_{i}"):
                assert_data_not_encoded(
                    backend.configuration().to_dict(), good_keys, good_keys_prefixes
                )

    def test_backend_properties(self):
        """Test deserializing backend properties."""
        service = self.service
        instance = None
        backends = service.backends(operational=True, simulator=False, instance=instance)

        # Known keys that look like a serialized object.
        good_keys = ("gates.qubits", "qubits.name", "backend_version", "general_qlists.qubits")

        for i, backend in enumerate(backends):
            with self.subTest(msg=f"backend_{i}"):
                try:
                    properties = backend.properties()
                except RequestsApiError as ex:
                    # Some backends might not be able to fetch properties.
                    if ex.status_code == 404:
                        properties = None
                if properties:
                    assert_data_not_encoded(properties.to_dict(), good_keys)
