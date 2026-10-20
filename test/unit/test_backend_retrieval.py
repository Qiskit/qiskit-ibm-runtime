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

"""Backends Filtering Test."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime.accounts import Account
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend, FakeTorino
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..account import get_account_config_contents, temporary_account_config_file
from ..registries import Backend, OneInstanceNoBackendsRegistry

if TYPE_CHECKING:
    from ..registries import BaseRegistry


class TestBackendFilters:
    """Qiskit Backend Filtering Tests."""

    def test_backend_instance_warnings(
        self, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test backend instance warnings."""
        service = QiskitRuntimeService(token="my_token")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.backends()
        assert "Loading instance" in caplog.messages[0]

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.backend("common_backend")
        assert "Using instance" in caplog.messages[0]

    def test_instance_auto_suppresses_backends_loading_warning(
        self, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """instance='auto' must suppress 'Loading instance' warnings in backends()."""
        # Create service outside the log capture so init's "Loading account" doesn't interfere.
        service = QiskitRuntimeService(token="my_token", instance="auto")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.backends()
        assert not caplog.records

    def test_instance_auto_suppresses_backend_using_warning(
        self, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """instance='auto' must suppress 'Using instance' warning when looking up by name."""
        # Create service outside the log capture so init's "Loading account" doesn't interfere.
        service = QiskitRuntimeService(token="my_token", instance="auto")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.backend("common_backend")
        assert not caplog.records

    def test_saved_account_instance_auto_suppresses_warnings(
        self, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A saved account with instance='auto' must suppress backend instance warnings."""
        saved_account = Account.create_account(
            channel="ibm_quantum_platform", token="my_token", instance="auto"
        )
        with mock.patch.object(
            QiskitRuntimeService, "_discover_account", return_value=saved_account
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token")

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.backends()
        assert not caplog.records
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.backend("common_backend")
        assert not caplog.records

    def test_no_filter(self, registry: BaseRegistry) -> None:
        """Test no filtering."""
        service = QiskitRuntimeService(token="my_token")
        # QiskitRuntimeService with DefaultRegistry by default creates 3 backends.
        backend_name = [back.name for back in service.backends()]
        assert len(backend_name) == 3

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_filter_mock_devices(self, registry: BaseRegistry) -> None:
        """Test filtering by configuration properties."""
        registry.add_backend(Backend("ibm_foo"))
        registry.add_backend(Backend("mock_foo", is_mock=True))

        # By default, backends() should exclude mock devices.
        service = QiskitRuntimeService(token="my_token")
        backends = service.backends()
        assert len(backends) == 1

        # When passing the flag, backends() should include mock devices.
        service = QiskitRuntimeService(token="my_token")
        backends = service.backends(include_mocks=True)
        assert len(backends) == 2

    @pytest.mark.parametrize("backend_name", ["common_backend", "unique_backend_a"])
    def test_filter_by_name(self, backend_name: str, registry: BaseRegistry) -> None:
        """Test filtering by name."""
        service = QiskitRuntimeService(token="my_token")

        backend_names = [back.name for back in service.backends(name=backend_name)]
        assert len(backend_names) == 1

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_filter_config_properties(self, registry: BaseRegistry) -> None:
        """Test filtering by configuration properties."""
        n_qubits = 5
        backend_5q = Backend("5q")
        backend_5q.configuration.update({"n_qubits": 5, "local": False})
        backend_10q = Backend("10q")
        backend_10q.configuration.update({"n_qubits": 10, "local": False})
        backend_5q2 = Backend("5q2")
        backend_5q2.configuration.update({"n_qubits": 5, "local": True})
        registry.add_backend(backend_5q)
        registry.add_backend(backend_10q)
        registry.add_backend(backend_5q2)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(n_qubits=n_qubits, local=False)
        assert len(filtered_backends) == 1
        assert n_qubits == filtered_backends[0].configuration().n_qubits
        assert not filtered_backends[0].configuration().local

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_filter_status_dict(self, registry: BaseRegistry) -> None:
        """Test filtering by dictionary of mixed status/configuration properties."""
        backend_1 = Backend("backend_1")
        backend_1.configuration.update({"simulator": True})
        backend_2 = Backend("backend_2")
        backend_2.configuration.update({"simulator": True})
        backend_3 = Backend("backend_3")
        backend_3.configuration.update({"simulator": False})
        backend_4 = Backend("backend_4", status="offline")
        backend_4.configuration.update({"simulator": True})
        registry.add_backend(backend_1)
        registry.add_backend(backend_2)
        registry.add_backend(backend_3)
        registry.add_backend(backend_4)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(
            operational=True,  # from status
            simulator=True,  # from configuration
        )
        assert len(filtered_backends) == 2
        for backend in filtered_backends:
            assert backend.status().operational
            assert backend.configuration().simulator

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_filter_config_callable(self, registry: BaseRegistry) -> None:
        """Test filtering by lambda function on configuration properties."""
        n_qubits = 5
        backend_5q = Backend("5q")
        backend_5q.configuration.update({"n_qubits": n_qubits})
        backend_10q = Backend("10q")
        backend_10q.configuration.update({"n_qubits": n_qubits * 2})
        backend_4q = Backend("4q")
        backend_4q.configuration.update({"n_qubits": n_qubits - 1})
        registry.add_backend(backend_5q)
        registry.add_backend(backend_10q)
        registry.add_backend(backend_4q)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(filters=lambda x: (x.configuration().n_qubits >= 5))
        assert len(filtered_backends) == 2
        for backend in filtered_backends:
            assert backend.configuration().n_qubits >= n_qubits

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_least_busy_use_fractional_gates_skips_backend_without_rzz(
        self, registry: BaseRegistry
    ) -> None:
        """When use_fractional_gates=True, least_busy skips backends missing rzz."""
        registry.add_backend(Backend.from_(FakeTorino, queue_length=5))
        registry.add_backend(Backend.from_(FakeFractionalBackend, queue_length=10))

        service = QiskitRuntimeService(token="my_token")
        backend = service.least_busy(use_fractional_gates=True)
        assert backend.name == "fake_fractional"
        assert "rzz" in backend.basis_gates

    def test_least_busy_use_fractional_gates_no_qualifying_backend(
        self, registry: BaseRegistry
    ) -> None:
        """When use_fractional_gates=True and no backend has rzz, raise an error."""
        service = QiskitRuntimeService(token="my_token")
        with pytest.raises(QiskitBackendNotFoundError):
            service.least_busy(use_fractional_gates=True)

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_least_busy_use_fractional_gates_false_ignores_rzz(
        self, registry: BaseRegistry
    ) -> None:
        """When use_fractional_gates=False (default), least_busy returns the least busy backend."""
        registry.add_backend(Backend.from_(FakeTorino, queue_length=5))
        registry.add_backend(Backend.from_(FakeFractionalBackend, queue_length=10))

        service = QiskitRuntimeService(token="token")
        backend = service.least_busy(use_fractional_gates=False)
        assert backend.name == "ibm_torino"

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_least_busy_excludes_mock(self, registry: BaseRegistry) -> None:
        """least_busy must not include mock devices."""
        registry.add_backend(Backend.from_(FakeTorino, name="not_mock_device", queue_length=10))
        registry.add_backend(
            Backend.from_(FakeTorino, name="mock_device", queue_length=5, is_mock=True)
        )

        service = QiskitRuntimeService(token="token")
        backend = service.least_busy()
        assert backend.name == "not_mock_device"

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_filter_least_busy(self, registry: BaseRegistry) -> None:
        """Test filtering by least busy function."""
        registry.add_backend(Backend("backend1", queue_length=10))
        registry.add_backend(Backend("backend2", queue_length=20))
        registry.add_backend(Backend("backend3", queue_length=1, status="offline"))
        registry.add_backend(Backend("backend4", queue_length=15))

        service = QiskitRuntimeService(token="my_token")
        backend = service.least_busy()
        assert backend.name == "backend1"

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_filter_min_num_qubits(self, registry: BaseRegistry) -> None:
        """Test filtering by minimum number of qubits."""
        n_qubits = 5
        backend_5q = Backend("5q")
        backend_5q.configuration.update({"n_qubits": n_qubits})
        backend_10q = Backend("10q")
        backend_10q.configuration.update({"n_qubits": n_qubits * 2})
        backend_4q = Backend("4q")
        backend_4q.configuration.update({"n_qubits": n_qubits - 1})
        registry.add_backend(backend_5q)
        registry.add_backend(backend_10q)
        registry.add_backend(backend_4q)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(min_num_qubits=n_qubits)
        assert len(filtered_backends) == 2
        for backend in filtered_backends:
            assert backend.configuration().n_qubits >= n_qubits


class TestGetBackend:
    """Test getting a backend."""

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_get_backend_properties(self, registry: BaseRegistry) -> None:
        """Test that a backend's properties are loaded into its target."""
        registry.add_backend(Backend.from_(FakeTorino))

        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_torino")

        t1s = sorted(p.t1 for p in backend.target.qubit_properties)
        sx_errors = sorted(backend.target["sx"][q].error for q in backend.target["sx"])
        cz_errors = sorted(backend.target["cz"][p].error for p in backend.target["cz"])

        # Check right number of gates/properties loaded
        assert len(t1s) == backend.num_qubits
        assert len(sx_errors) == backend.num_qubits
        assert len(cz_errors) == 300
        # Check that the right property values were loaded
        assert t1s[0] == pytest.approx(3.163e-6, abs=0.5e-8)
        assert t1s[-1] == pytest.approx(3.077e-4, abs=0.5e-6)
        assert sx_errors[0] == pytest.approx(1.1358e-4, abs=0.5e-7)
        assert sx_errors[-1] == pytest.approx(0.01738, abs=0.5e-5)
        assert cz_errors[0] == pytest.approx(0.001495, abs=0.5e-5)
        assert cz_errors[-1] == pytest.approx(1.0, abs=0.5e-5)

    @pytest.mark.parametrize(
        "use_fractional",
        [True, False, None],
        ids=["with_fractional", "without_fractional", "without_filtering"],
    )
    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_get_backend_with_fractional_optin(
        self, use_fractional: bool | None, registry: BaseRegistry
    ) -> None:
        """Test getting backend with fractional gate opt-in.

        This test can be modified when the IBM backend architecture changes in future.
        In our backend as of today, fractional gates and dynamic circuits are
        only exclusively supported.

        This test is originally written in 2024.05.31
        """
        registry.add_backend(Backend.from_(FakeFractionalBackend))
        service = QiskitRuntimeService(token="my_token")

        test_backend = service.backends("fake_fractional", use_fractional_gates=use_fractional)[0]
        assert ("rx" in test_backend.target) == (use_fractional or use_fractional is None)
        assert ("rzz" in test_backend.target) == (use_fractional or use_fractional is None)
        assert "if_else" in test_backend.target.operation_names
        assert "while_loop" in test_backend.target.operation_names

        if use_fractional or use_fractional is None:
            assert test_backend.target["rx"][(0,)].error == pytest.approx(0.00019, abs=0.5e-5)

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_backend_with_and_without_fractional_from_same_service(
        self, registry: BaseRegistry
    ) -> None:
        """Test getting backend with and without fractional gates from the same service.

        Backend with and without opt-in must be different object.
        """
        registry.add_backend(Backend.from_(FakeFractionalBackend))
        service = QiskitRuntimeService(token="my_token")

        backend_with_fg = service.backend("fake_fractional", use_fractional_gates=True)
        assert "rx" in backend_with_fg.target

        backend_without_fg = service.backend("fake_fractional", use_fractional_gates=False)
        assert "rx" not in backend_without_fg.target
        assert "rx" in backend_with_fg.target

        assert backend_with_fg is not backend_without_fg

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_backend_with_custom_calibration(self, registry: BaseRegistry) -> None:
        """Test listing a backend with a custom calibration and reverting to default."""
        registry.add_backend(
            Backend(
                "ibm_torino",
                calibrations={"abc1234": {"supported_instructions": ["while_loop"]}},
            )
        )
        service = QiskitRuntimeService(token="my_token")

        backend_with_calibration = service.backends("ibm_torino", calibration_id="abc1234")[0]
        assert backend_with_calibration.calibration_id == "abc1234"
        assert "while_loop" in backend_with_calibration.supported_instructions

        default_backend = service.backends("ibm_torino")[0]
        assert default_backend.calibration_id is None
        assert "while_loop" not in default_backend.supported_instructions

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_backend_with_invalid_calibration(self, registry: BaseRegistry) -> None:
        """Test that retrieving a backend with an invalid calibration fails."""
        registry.add_backend(
            Backend(
                "ibm_torino",
                calibrations={"abc1234": {"supported_instructions": ["while_loop"]}},
            )
        )
        service = QiskitRuntimeService(token="my_token")

        with pytest.raises(QiskitBackendNotFoundError):
            service.backend("ibm_torino", calibration_id="invalid")

    @pytest.mark.parametrize(
        "use_account",
        [
            # NamedTemporaryFiles not supported in Windows.
            pytest.param(
                True,
                marks=pytest.mark.skipif(os.name == "nt", reason="Test not supported in Windows"),
            ),
            False,
        ],
    )
    def test_retrieve_mock_backend(
        self, use_account: bool, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test retrieving a backend that is not in the default list of backends.

        This test exercises the case where a backend is retrieved via `backend()`, and that backend
        is not returned in the `backends()` method by default.
        """
        # Make all backends mock devices.
        for instance in registry.backends.values():
            for backend in instance.values():
                backend.is_mock = True

        instance_a = registry.instances["a"]
        instance_b = registry.instances["b"]

        # Initialize the service, by token or with accounts.
        if use_account:
            with temporary_account_config_file(
                get_account_config_contents("account_a", token="my_token", instance="a")
                | get_account_config_contents("account_b", token="my_token", instance="b")
            ):
                service = QiskitRuntimeService(instance=registry.instances["a"].crn)
        else:
            service = QiskitRuntimeService(token="my_token")

        # Ensure that no backend appears in the backends list by default.
        assert service.backends() == []

        # Retrieve an existing mocked backend (available in several instances).
        backend = service.backend("common_backend")
        assert backend.name == "common_backend"
        assert backend._instance == instance_a.crn
        assert backend.is_mock

        # Retrieve an existing mocked backend (available in several instances), passing instance.
        backend = service.backend("common_backend", instance="b")
        assert backend.name == "common_backend"
        assert backend._instance == instance_b.crn
        assert backend.is_mock

        # Retrieve an existing mocked backend (available in one instance).
        backend = service.backend("unique_backend_a")
        assert backend.name == "unique_backend_a"
        assert backend._instance == instance_a.crn
        assert backend.is_mock

        # Retrieve an existing mocked backend (available in one instance), with wrong instance.
        caplog.clear()
        with (
            pytest.raises(QiskitBackendNotFoundError),
            caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"),
        ):
            backend = service.backend("unique_backend_a", instance="b")
        assert not caplog.records

    @pytest.mark.parametrize(
        "use_account",
        [
            # NamedTemporaryFiles not supported in Windows.
            pytest.param(
                True,
                marks=pytest.mark.skipif(os.name == "nt", reason="Test not supported in Windows"),
            ),
            False,
        ],
    )
    def test_retrieve_mock_backend_instance_auto(
        self, use_account: bool, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test retrieving a backend not in default the list of backends, with instance `auto`.

        This test exercises the case where a backend is retrieved via `backend()`, and that backend
        is not returned in the `backends()` method by default.

        When passing `instance=auto` to `QiskitRuntimeService()`, warnings should not be emitted
        when guessing instances.
        """
        # Make all backends mock devices.
        for instance in registry.backends.values():
            for backend in instance.values():
                backend.is_mock = True

        # Initialize the service, by token or with accounts.
        if use_account:
            with temporary_account_config_file(
                get_account_config_contents("account_a", token="my_token", instance="a")
                | get_account_config_contents("account_b", token="my_token", instance="b")
            ):
                service = QiskitRuntimeService(instance="auto")
        else:
            service = QiskitRuntimeService(token="my_token", instance="auto")

        # Ensure that no backend appears in the backends list.
        assert service.backends() == []

        # Retrieve an existing backend (available in one instance).
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            backend = service.backend("unique_backend_b")
        assert not caplog.records
        assert backend.name == "unique_backend_b"
        assert backend._instance == registry.instances["b"].crn
