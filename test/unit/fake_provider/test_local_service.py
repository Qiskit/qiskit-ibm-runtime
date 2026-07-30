# This code is part of Qiskit.
#
# (C) Copyright IBM 2020-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test of generated fake backends."""

from ddt import data, ddt
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime.fake_provider import FakeAlgiers, FakeProviderForBackendV2, FakeTorino
from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService

from ...ibm_test_case import IBMTestCase


@ddt
class QiskitRuntimeLocalServiceTest(IBMTestCase):
    """Qiskit runtime local service test."""

    def test_backend(self):
        """Tests the ``backend`` method."""
        service = QiskitRuntimeLocalService()
        self.assertIsInstance(service.backend(), FakeBackendV2)
        self.assertIsInstance(service.backend("fake_algiers"), FakeAlgiers)
        self.assertIsInstance(service.backend("fake_torino"), FakeTorino)

    def test_backends(self):
        """Tests the ``backends`` method."""
        all_backends = QiskitRuntimeLocalService().backends()
        expected = FakeProviderForBackendV2().backends()
        self.assertEqual(len(all_backends), len(expected))

        for b1, b2 in zip(all_backends, expected):
            self.assertIsInstance(b1, b2.__class__)

    def test_backends_name_filter(self):
        """Tests the ``name`` filter of the ``backends`` method."""
        backends = QiskitRuntimeLocalService().backends("fake_torino")
        self.assertEqual(len(backends), 1)
        self.assertIsInstance(backends[0], FakeTorino)

    def test_backends_min_num_qubits_filter(self):
        """Tests the ``min_num_qubits`` filter of the ``backends`` method.

        The `min_num_qubits` logic forces the properties of all backends to be loaded for building
        the target, making the test slightly slow.
        """
        for b in QiskitRuntimeLocalService().backends(min_num_qubits=27):
            self.assertGreaterEqual(b.num_qubits, 27)

    @data(False, True)
    def test_backends_dynamic_circuits_filter(self, supports):
        """Tests the ``dynamic_circuits`` filter of the ``backends`` method."""
        for b in QiskitRuntimeLocalService().backends(dynamic_circuits=supports):
            self.assertEqual(b._supports_dynamic_circuits(), supports)

    def test_backends_filters(self):
        """Tests the ``filters`` argument of the ``backends`` method."""
        for b in QiskitRuntimeLocalService().backends(
            filters=lambda b: (b.online_date.year == 2021)
        ):
            self.assertEqual(b.online_date.year, 2021)

        for b in QiskitRuntimeLocalService().backends(
            filters=lambda b: (b.dtm is not None and b.dtm < 5e-10)
        ):
            self.assertLess(b.dtm, 5e-10)

    def test_backends_filters_combined(self):
        """Tests the ``backends`` method with more than one filter."""
        service = QiskitRuntimeLocalService()

        backends1 = service.backends(
            name="fake_torino", min_num_qubits=27, filters=lambda b: (b.online_date.year == 2023)
        )
        self.assertEqual(len(backends1), 1)
        self.assertIsInstance(backends1[0], FakeTorino)
        self.assertEqual(backends1[0].online_date.year, 2023)

    def test_backends_errors(self):
        """Tests the errors raised by the ``backends`` method."""
        service = QiskitRuntimeLocalService()

        with self.assertRaises(QiskitBackendNotFoundError):
            service.backends("torino")
        with self.assertRaises(QiskitBackendNotFoundError):
            service.backends("fake_torino", filters=lambda b: (b.online_date.year == 1992))

    def test_least_busy(self):
        """Tests the ``least_busy`` method."""
        self.assertIsInstance(QiskitRuntimeLocalService().least_busy(), FakeBackendV2)
