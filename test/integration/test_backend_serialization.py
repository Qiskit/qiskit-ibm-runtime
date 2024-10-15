# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test deserializing server data."""

from typing import Any, Dict, Set, Optional

import dateutil.parser

from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test, production_only


class TestSerialization(IBMIntegrationTestCase):
    """Test data serialization."""

    @production_only
    @run_integration_test
    def test_backend_configuration(self, service):
        """Test deserializing backend configuration."""
        instance = self.dependencies.instance if service.channel == "ibm_quantum" else None
        backends = service.backends(operational=True, simulator=False, instance=instance)

        # Known keys that look like a serialized complex number.
        good_keys = (
            "coupling_map",
            "qubit_lo_range",
            "meas_lo_range",
            "gates.coupling_map",
            "meas_levels",
            "qubit_channel_mapping",
            "backend_version",
            "rep_delay_range",
            "processor_type.revision",
            "coords",
        )
        good_keys_prefixes = ("channels",)

        for backend in backends:
            with self.subTest(backend=backend):
                self._verify_data(backend.configuration().to_dict(), good_keys, good_keys_prefixes)

    @run_integration_test
    def test_pulse_defaults(self, service):
        """Test deserializing backend configuration."""
        instance = self.dependencies.instance if service.channel == "ibm_quantum" else None
        backends = service.backends(operational=True, open_pulse=True, instance=instance)
        if not backends:
            self.skipTest("Need pulse backends.")

        # Known keys that look like a serialized complex number.
        good_keys = ("cmd_def.qubits", "cmd_def.sequence.ch")

        for backend in backends:
            with self.subTest(backend=backend):
                self._verify_data(backend.defaults().to_dict(), good_keys)

    @run_integration_test
    def test_backend_properties(self, service):
        """Test deserializing backend properties."""
        instance = self.dependencies.instance if service.channel == "ibm_quantum" else None
        backends = service.backends(operational=True, simulator=False, instance=instance)

        # Known keys that look like a serialized object.
        good_keys = ("gates.qubits", "qubits.name", "backend_version", "general_qlists.qubits")

        for backend in backends:
            with self.subTest(backend=backend):
                properties = backend.properties()
                if properties:
                    self._verify_data(properties.to_dict(), good_keys)

    def _verify_data(
        self, data: Dict, good_keys: tuple, good_key_prefixes: Optional[tuple] = None
    ) -> None:
        """Verify that the input data does not contain serialized objects.

        Args:
            data: Data to validate.
            good_keys: A list of known keys that look serialized objects.
            good_key_prefixes: A list of known prefixes for keys that look like
                serialized objects.
        """
        suspect_keys: Set[Any] = set()
        _find_potential_encoded(data, "", suspect_keys)
        # Remove known good keys from suspect keys.
        for gkey in good_keys:
            try:
                suspect_keys.remove(gkey)
            except KeyError:
                pass
        if good_key_prefixes:
            for gkey in good_key_prefixes:
                suspect_keys = {ckey for ckey in suspect_keys if not ckey.startswith(gkey)}
        self.assertFalse(suspect_keys)


def _find_potential_encoded(data: Any, c_key: str, tally: set) -> None:
    """Find data that may be in JSON serialized format.

    Args:
        data: Data to be recursively traversed to find suspects.
        c_key: Key of the field currently being traversed.
        tally: Keys of fields that look suspect.
    """
    if _check_encoded(data):
        tally.add(c_key)

    if isinstance(data, list):
        for item in data:
            _find_potential_encoded(item, c_key, tally)
    elif isinstance(data, dict):
        for key, value in data.items():
            full_key = c_key + "." + str(key) if c_key else str(key)
            _find_potential_encoded(value, full_key, tally)


def _check_encoded(data):
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


def _array_to_list(data):
    """Convert numpy arrays to lists."""
    for key, value in data.items():
        if hasattr(value, "tolist"):
            data[key] = value.tolist()
        elif isinstance(value, dict):
            _array_to_list(value)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    value[index] = _array_to_list(item)

    return data
