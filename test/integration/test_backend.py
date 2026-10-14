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

"""Tests for backend functions using real runtime service."""

from __future__ import annotations

import copy
import logging
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.providers.backend import QubitProperties
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.transpiler.target import Target

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from ..utils import bell

if TYPE_CHECKING:
    from qiskit_ibm_runtime.ibm_backend import IBMBackend

    from .dependencies import Dependencies


@pytest.fixture(scope="class")
def backend(dependencies: Dependencies) -> IBMBackend:
    """Return the backend used by the tests in the class, from the environment configuration."""
    return dependencies.service.backend(dependencies.qpu)


def get_mock_backend_pair(service: QiskitRuntimeService) -> tuple[IBMBackend, IBMBackend]:
    """Return a pair of backends: real backend, mocked backend."""
    backends = service.backends(include_mocks=True)

    try:
        # Find a suitable backend that has a mock backend.
        dry_run_backend = next(
            backend
            for backend in backends
            if backend.name.startswith("mock_") and backend.status().status_msg == "active"
        )
        backend_name = re.sub(r"^[^_]+", "ibm", dry_run_backend.name)
        return service.backend(backend_name), dry_run_backend
    except (StopIteration, QiskitBackendNotFoundError):
        pytest.skip("No backend with corresponding mock backend available.")


class TestIntegrationBackend:
    """Integration tests for backend functions."""

    def test_least_busy(self, dependencies: Dependencies) -> None:
        """Test the least busy method."""
        service = dependencies.service
        # test passing an instance
        instance = dependencies.instance
        backend = service.least_busy(instance=instance)
        assert instance == backend._instance

        # test when there is no instance
        service_with_no_default_instance = QiskitRuntimeService(
            token=dependencies.token,
            channel="ibm_quantum_platform",
            url=dependencies.url,
        )
        backend = service_with_no_default_instance.least_busy()
        assert backend

    def test_backends(self, dependencies: Dependencies) -> None:
        """Test getting all backends."""
        service = dependencies.service
        backends = service.backends()
        assert backends
        backend_names = [back.name for back in backends]
        assert len(backend_names) == len(set(backend_names))

    def test_get_backend(self, dependencies: Dependencies) -> None:
        """Test getting a backend."""
        service = dependencies.service
        backends = service.backends()
        backend = service.backend(backends[0].name)
        assert backend

    def test_target_reset(self, dependencies: Dependencies) -> None:
        """Test confirming target contains reset."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        assert "reset" in backend.target

    def test_backends_physical_qubits(self, dependencies: Dependencies) -> None:
        """All backends should have a `physical_qubits` property."""
        service = dependencies.service
        backends = service.backends()

        for backend in backends:
            assert isinstance(backend.physical_qubits, int)

    def test_backends_include_mocks(self, dependencies: Dependencies) -> None:
        """`service.backends()` should respect the `include_mocks` flag."""
        service = dependencies.service
        # Skip the test if there are no mock backends.
        get_mock_backend_pair(service)

        backends_no_mocks = service.backends()
        backends_include_mocks = service.backends(include_mocks=True)

        assert len(backends_include_mocks) > len(backends_no_mocks)
        assert not any(backend.name.startswith("mock") for backend in backends_no_mocks)
        assert not any(backend.is_mock for backend in backends_no_mocks)
        assert any(backend.name.startswith("mock") for backend in backends_include_mocks)
        assert any(backend.is_mock for backend in backends_include_mocks)


class TestIBMBackend:
    """Test ibm_backend module."""

    def test_backend_service(self, backend: IBMBackend) -> None:
        """Check if the service property is set."""
        assert isinstance(backend.service, QiskitRuntimeService)

    @pytest.mark.production
    def test_backend_target(self, backend: IBMBackend) -> None:
        """Check if the target property is set."""
        assert backend.target is not None
        assert isinstance(backend.target, Target)

    @pytest.mark.production
    def test_backend_target_history(self, backend: IBMBackend) -> None:
        """Check retrieving backend target_history."""
        assert backend.target_history() is not None
        assert backend.target_history(datetime=datetime.now() - timedelta(30)) is not None

    @pytest.mark.production
    def test_properties_not_cached_target_history(self, backend: IBMBackend) -> None:
        """Check backend properties is not cached in target_history()."""
        properties = backend.properties()
        backend.target_history(datetime=datetime.now() - timedelta(60))
        assert properties == backend.properties()

    def test_backend_target_refresh(self, backend: IBMBackend) -> None:
        """Test refreshing the backend target."""
        old_target = backend.target
        old_configuration = backend.configuration()
        old_properties = backend.properties()
        backend.refresh()
        new_target = backend.target
        assert old_target != new_target
        assert old_configuration is not backend.configuration()
        assert old_properties is not backend.properties()

    def test_backend_qubit_properties(self, backend: IBMBackend) -> None:
        """Check if the qubit properties are set."""
        assert backend.qubit_properties(0) is not None

    def test_backend_simulator(self, backend: IBMBackend) -> None:
        """Test if a configuration attribute (ex: simulator) is available as backend attribute."""
        assert backend.simulator is not None
        assert backend.simulator == backend.configuration().simulator

    def test_backend_status(self, backend: IBMBackend) -> None:
        """Check the status of a real chip."""
        assert backend.status().operational

    def test_backend_properties(self, backend: IBMBackend) -> None:
        """Check the properties of calibration of a real chip."""
        properties = backend.properties()
        properties_today = backend.properties(datetime=datetime.today())
        assert properties is not None
        assert properties_today is not None
        assert properties.backend_version == properties_today.backend_version

    def test_backend_configuration(self, backend: IBMBackend) -> None:
        """Check the backend configuration of each backend."""
        assert backend.configuration() is not None

    @pytest.mark.production
    def test_backend_invalid_attribute(self, backend: IBMBackend) -> None:
        """Check if AttributeError is raised when an invalid backend attribute is accessed."""
        with pytest.raises(AttributeError):
            backend.foobar

    def test_backend_deepcopy(self, backend: IBMBackend) -> None:
        """Test that deepcopy on IBMBackend works correctly."""
        backend_copy = copy.deepcopy(backend)
        assert backend_copy.name == backend.name
        assert backend_copy.configuration().basis_gates == backend.configuration().basis_gates
        if backend.properties():
            assert (
                backend_copy.properties().last_update_date == backend.properties().last_update_date
            )
        assert backend_copy._instance == backend._instance
        assert backend_copy._api_client._session.base_url == backend._api_client._session.base_url

    def test_backend_pending_jobs(self, dependencies: Dependencies) -> None:
        """Test pending jobs are returned."""
        service = dependencies.service
        backends = service.backends()
        assert any(backend.status().pending_jobs >= 0 for backend in backends)

    def test_backend_fetch_all_qubit_properties(self, backend: IBMBackend) -> None:
        """Check retrieving properties of all qubits."""
        num_qubits = backend.num_qubits
        qubits = list(range(num_qubits))
        qubit_properties = backend.qubit_properties(qubits)
        assert len(qubit_properties) == num_qubits
        for i in qubits:
            assert isinstance(qubit_properties[i], QubitProperties)

    def test_sim_backend_options(self, backend: IBMBackend) -> None:
        """Test simulator backend options."""
        backend.options.shots = 2048
        backend.set_options(memory=True)
        sampler = Sampler(mode=backend)
        isa_circuit = transpile(bell(), backend)
        inputs = sampler.run([isa_circuit], shots=1).inputs
        assert inputs["pubs"][0][2] == 1

    @pytest.mark.production
    def test_paused_backend_warning(
        self, backend: IBMBackend, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a warning is given when running jobs on a paused backend."""
        paused_status = backend.status()
        paused_status.status_msg = "internal"
        monkeypatch.setattr(backend, "status", lambda: paused_status)
        isa_circuit = transpile(bell(), backend)
        with pytest.warns(Warning):
            sampler = Sampler(mode=backend)
            sampler.run([isa_circuit])

    def test_retrieve_backend_not_exist(self, dependencies: Dependencies) -> None:
        """Test that an error is raised when retrieving a backend that does not exist."""
        service = dependencies.service
        with pytest.raises(QiskitBackendNotFoundError):
            service.backend("nonexistent_backend")

    def test_too_many_qubits_in_circuit(self, backend: IBMBackend) -> None:
        """Check error message if circuit contains more qubits than supported on the backend."""
        num = len(backend.properties().qubits)
        num_qubits = num + 1
        circuit = QuantumCircuit(num_qubits, num_qubits)
        with pytest.raises(IBMInputValueError) as err:
            sampler = Sampler(mode=backend)
            job = sampler.run([circuit])
            job.cancel()
        assert f"circuit has {num_qubits} qubits but the target system requires {num}" in str(
            err.value
        )

    def test_use_fractional_gates_flag(self, dependencies: Dependencies) -> None:
        """Test use_fractional_gates returns correct backend config."""
        service = dependencies.service
        try:
            real_device_name = "alt_fez"
            real_device_no_fg = service.backend(real_device_name, use_fractional_gates=False)
            real_device_fg = service.backend(real_device_name, use_fractional_gates=True)
        except QiskitBackendNotFoundError:
            pytest.skip("Real backend not available.")
        assert "rzz" in real_device_fg.basis_gates
        assert "rzz" not in real_device_no_fg.basis_gates

    def test_backend_fractional_gates_error(
        self, backend: IBMBackend, dependencies: Dependencies
    ) -> None:
        """Test that use_fractional_gates = True raises error for unsupported backends."""
        service = dependencies.service
        if "rzz" in backend.basis_gates or "rx" in backend.basis_gates:
            pytest.skip(f"Backend {backend.name} supports fractional gates, no error.")
        with pytest.raises(
            IBMInputValueError,
            match=(
                f"Backend '{backend.name}' does not support fractional gates, "
                "but use_fractional_gates was set to True."
            ),
        ):
            service.backend(backend.name, use_fractional_gates=True)

    def test_backend_fractional_gates_cache_behavior(self, dependencies: Dependencies) -> None:
        """Test backend config cache/refresh logic for use_fractional_gates."""
        service = dependencies.service
        try:
            real_device_name = "ibm_miami"
            backend_fg = service.backend(real_device_name, use_fractional_gates=True)
            backend_fg2 = service.backend(real_device_name, use_fractional_gates=True)
            backend_no_fg = service.backend(real_device_name, use_fractional_gates=False)
            backend_no_fg2 = service.backend(real_device_name, use_fractional_gates=False)
            backend_fg3 = service.backend(real_device_name, use_fractional_gates=True)
        except QiskitBackendNotFoundError:
            pytest.skip("Real backend not available.")

        # The cache is used for repeated use_fractional_gates=True.
        assert backend_fg is backend_fg2
        # The configuration is refreshed when use_fractional_gates changes.
        assert backend_fg is not backend_no_fg
        # The cache is used to create the backend object.
        assert backend_no_fg is backend_no_fg2
        # The configuration is refreshed when use_fractional_gates changes.
        assert backend_no_fg2 is not backend_fg3

    def test_renew_backend_properties(
        self, backend: IBMBackend, dependencies: Dependencies
    ) -> None:
        """Test renewed backend property."""
        service = dependencies.service
        name = backend.name
        fetched_backend = service.backend(name)
        basis_gates = copy.copy(fetched_backend.basis_gates)
        # Modify a property.
        fetched_backend.basis_gates.remove(basis_gates[0])
        # Renew backend.
        renewed_backend = service.backend(name)
        assert renewed_backend.basis_gates == basis_gates

    def test_backend_calibration_id(
        self,
        backend: IBMBackend,
        dependencies: Dependencies,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test calibration_id is used when fetching the configuration."""
        service = dependencies.service
        name = backend.name
        calibration_id = "invalid_id"
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            with pytest.raises(QiskitBackendNotFoundError):
                service.backend(name, calibration_id=calibration_id)

        assert calibration_id in caplog.text

    def test_run_dry_run(self, dependencies: Dependencies) -> None:
        """Test `run` using the `dry_run` flag.

        This test does not use ``dependencies.qpu``, but instead attempts to find a backend that
        can be used for ``dry_run`` mode, skipping if not.
        """
        service = dependencies.service
        backend, dry_run_backend = get_mock_backend_pair(service)

        isa_circuit = transpile(bell(), backend)
        sampler = Sampler(mode=backend)
        job = sampler.run([isa_circuit], dry_run=True)
        assert job.backend().name == dry_run_backend.name
