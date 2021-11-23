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

"""Test serializing and deserializing data sent to the server."""

from unittest import skipIf
from typing import Any, Dict, Optional

import dateutil.parser
from qiskit.circuit import Parameter
from qiskit.version import VERSION as terra_version

from qiskit_ibm_runtime.utils.json_encoder import IBMJsonEncoder

from ..decorators import requires_provider
from ..ibm_test_case import IBMTestCase


class TestSerialization(IBMTestCase):
    """Test data serialization."""

    @classmethod
    @requires_provider
    def setUpClass(cls, service, hub, group, project):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.service = service
        cls.hub = hub
        cls.group = group
        cls.project = project
        cls.sim_backend = service.get_backend('ibmq_qasm_simulator', hub=cls.hub,
                                              group=cls.group, project=cls.project)

    def test_backend_configuration(self):
        """Test deserializing backend configuration."""
        backends = self.service.backends(operational=True, simulator=False, hub=self.hub,
                                         group=self.group, project=self.project)

        # Known keys that look like a serialized complex number.
        good_keys = ('coupling_map', 'qubit_lo_range', 'meas_lo_range', 'gates.coupling_map',
                     'meas_levels', 'qubit_channel_mapping', 'backend_version', 'rep_delay_range',
                     'processor_type.revision')
        good_keys_prefixes = ('channels',)

        for backend in backends:
            with self.subTest(backend=backend):
                self._verify_data(backend.configuration().to_dict(),
                                  good_keys, good_keys_prefixes)

    def test_pulse_defaults(self):
        """Test deserializing backend configuration."""
        backends = self.service.backends(operational=True, open_pulse=True, hub=self.hub,
                                         group=self.group, project=self.project)
        if not backends:
            self.skipTest('Need pulse backends.')

        # Known keys that look like a serialized complex number.
        good_keys = ('cmd_def.qubits', 'cmd_def.sequence.ch')

        for backend in backends:
            with self.subTest(backend=backend):
                self._verify_data(backend.defaults().to_dict(), good_keys)

    def test_backend_properties(self):
        """Test deserializing backend properties."""
        backends = self.service.backends(operational=True, simulator=False, hub=self.hub,
                                         group=self.group, project=self.project)

        # Known keys that look like a serialized object.
        good_keys = ('gates.qubits', 'qubits.name', 'backend_version')

        for backend in backends:
            with self.subTest(backend=backend):
                properties = backend.properties()
                self._verify_data(properties.to_dict(), good_keys)

    def _verify_data(
            self,
            data: Dict,
            good_keys: tuple,
            good_key_prefixes: Optional[tuple] = None
    ):
        """Verify that the input data does not contain serialized objects.

        Args:
            data: Data to validate.
            good_keys: A list of known keys that look serialized objects.
            good_key_prefixes: A list of known prefixes for keys that look like
                serialized objects.
        """
        suspect_keys = set()
        _find_potential_encoded(data, '', suspect_keys)
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

    @skipIf(terra_version < '0.17', "Need Terra >= 0.17")
    def test_convert_complex(self):
        """Verify that real and complex ParameterExpressions are supported."""
        param = Parameter('test')
        self.assertEqual(IBMJsonEncoder().default(param.bind({param: 0.2})), 0.2)

        val = IBMJsonEncoder().default(param.bind({param: 0.2+0.1j}))
        self.assertEqual(val[0], 0.2)
        self.assertEqual(val[1], 0.1)


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
            full_key = c_key + '.' + str(key) if c_key else str(key)
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
        if hasattr(value, 'tolist'):
            data[key] = value.tolist()
        elif isinstance(value, dict):
            _array_to_list(value)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    value[index] = _array_to_list(item)

    return data
