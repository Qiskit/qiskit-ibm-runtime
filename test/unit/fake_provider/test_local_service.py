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

import pytest
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime.fake_provider import FakeAlgiers, FakeProviderForBackendV2, FakeTorino
from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService


class TestQiskitRuntimeLocalService:
    """Qiskit runtime local service test."""

    def test_backend(self) -> None:
        """Tests the ``backend`` method."""
        service = QiskitRuntimeLocalService()
        assert isinstance(service.backend(), FakeBackendV2)
        assert isinstance(service.backend("fake_algiers"), FakeAlgiers)
        assert isinstance(service.backend("fake_torino"), FakeTorino)

    def test_backends(self) -> None:
        """Tests the ``backends`` method."""
        all_backends = QiskitRuntimeLocalService().backends()
        expected = FakeProviderForBackendV2().backends()
        assert len(all_backends) == len(expected)

        for b1, b2 in zip(all_backends, expected):
            assert isinstance(b1, b2.__class__)

    def test_backends_name_filter(self) -> None:
        """Tests the ``name`` filter of the ``backends`` method."""
        backends = QiskitRuntimeLocalService().backends("fake_torino")
        assert len(backends) == 1
        assert isinstance(backends[0], FakeTorino)

    def test_backends_min_num_qubits_filter(self) -> None:
        """Tests the ``min_num_qubits`` filter of the ``backends`` method.

        The `min_num_qubits` logic forces the properties of all backends to be loaded for building
        the target, making the test slightly slow.
        """
        for b in QiskitRuntimeLocalService().backends(min_num_qubits=27):
            assert b.num_qubits >= 27

    @pytest.mark.parametrize("supports", [False, True])
    def test_backends_dynamic_circuits_filter(self, supports: bool) -> None:
        """Tests the ``dynamic_circuits`` filter of the ``backends`` method."""
        for b in QiskitRuntimeLocalService().backends(dynamic_circuits=supports):
            assert b._supports_dynamic_circuits() == supports

    def test_backends_filters(self) -> None:
        """Tests the ``filters`` argument of the ``backends`` method."""
        for b in QiskitRuntimeLocalService().backends(
            filters=lambda b: (b.online_date.year == 2021)
        ):
            assert b.online_date.year == 2021

        for b in QiskitRuntimeLocalService().backends(
            filters=lambda b: (b.dtm is not None and b.dtm < 5e-10)
        ):
            assert b.dtm < 5e-10

    def test_backends_filters_combined(self) -> None:
        """Tests the ``backends`` method with more than one filter."""
        service = QiskitRuntimeLocalService()

        backends1 = service.backends(
            name="fake_torino", min_num_qubits=27, filters=lambda b: (b.online_date.year == 2023)
        )
        assert len(backends1) == 1
        assert isinstance(backends1[0], FakeTorino)
        assert backends1[0].online_date.year == 2023

    def test_backends_errors(self) -> None:
        """Tests the errors raised by the ``backends`` method."""
        service = QiskitRuntimeLocalService()

        with pytest.raises(QiskitBackendNotFoundError):
            service.backends("torino")
        with pytest.raises(QiskitBackendNotFoundError):
            service.backends("fake_torino", filters=lambda b: (b.online_date.year == 1992))

    def test_least_busy(self) -> None:
        """Tests the ``least_busy`` method."""
        assert isinstance(QiskitRuntimeLocalService().least_busy(), FakeBackendV2)
