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
import pytest

from qiskit_ibm_runtime.api.exceptions import RequestsApiError

from .dependencies import integration_test_dependencies

if TYPE_CHECKING:
    from qiskit_ibm_runtime.ibm_backend import IBMBackend

    from .dependencies import Dependencies


def backend_names() -> list[str]:
    """Return the names of the backends to be tested."""
    try:
        dependencies = integration_test_dependencies()
    except pytest.skip.Exception:
        return []

    return [
        backend.name
        for backend in dependencies.service.backends(
            operational=True, simulator=False, instance=dependencies.instance
        )
    ]


@pytest.fixture
def backend(request: pytest.FixtureRequest, dependencies: Dependencies) -> IBMBackend:
    """Return the backend named by the indirect parametrization."""
    return dependencies.service.backend(request.param)


def assert_data(data: dict, good_keys: tuple, good_key_prefixes: tuple | None = None) -> None:
    """Assert that the input data does not contain serialized objects.

    Args:
        data: Data to validate.
        good_keys: A list of known keys that look serialized objects.
        good_key_prefixes: A list of known prefixes for keys that look like
            serialized objects.
    """
    suspect_keys: set[Any] = set()
    find_potential_encoded(data, "", suspect_keys)
    # Remove known good keys from suspect keys.
    for gkey in good_keys:
        try:
            suspect_keys.remove(gkey)
        except KeyError:
            pass
    if good_key_prefixes:
        for gkey in good_key_prefixes:
            suspect_keys = {ckey for ckey in suspect_keys if not ckey.startswith(gkey)}
    assert not suspect_keys


def find_potential_encoded(data: Any, c_key: str, tally: set) -> None:
    """Find data that may be in JSON serialized format.

    Args:
        data: Data to be recursively traversed to find suspects.
        c_key: Key of the field currently being traversed.
        tally: Keys of fields that look suspect.
    """
    if check_encoded(data):
        tally.add(c_key)

    if isinstance(data, list):
        for item in data:
            find_potential_encoded(item, c_key, tally)
    elif isinstance(data, dict):
        for key, value in data.items():
            full_key = c_key + "." + str(key) if c_key else str(key)
            find_potential_encoded(value, full_key, tally)


def check_encoded(data: list | str) -> bool:
    """Check if the input data is potentially in JSON serialized format."""
    if isinstance(data, list) and len(data) == 2 and all(isinstance(x, (float, int)) for x in data):
        return True
    elif isinstance(data, str):
        try:
            dateutil.parser.parse(data)
            return True
        except ValueError:
            pass
    return False


@pytest.mark.parametrize(
    "backend",
    [pytest.param(name, id=f"backend_{i}") for i, name in enumerate(backend_names(), 1)],
    indirect=True,
)
class TestSerialization:
    """Test data serialization.

    This class is parametrized with the names of the backends retrieved live from the service.
    """

    @pytest.mark.production
    def test_backend_configuration(self, backend: IBMBackend) -> None:
        """Test deserializing backend configuration."""
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

        assert_data(backend.configuration().to_dict(), good_keys, good_keys_prefixes)

    def test_backend_properties(self, backend: IBMBackend) -> None:
        """Test deserializing backend properties."""
        # Known keys that look like a serialized object.
        good_keys = ("gates.qubits", "qubits.name", "backend_version", "general_qlists.qubits")

        try:
            properties = backend.properties()
        except RequestsApiError as ex:
            # Some backends might not be able to fetch properties.
            if ex.status_code == 404:
                properties = None
        if properties:
            assert_data(properties.to_dict(), good_keys)
