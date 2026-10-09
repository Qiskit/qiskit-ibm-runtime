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

import os
import shutil
import tempfile
import unittest
from unittest import mock

from ddt import data, ddt
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import CZGate, ECRGate
from qiskit.utils import optionals

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2, fake_provider
from qiskit_ibm_runtime.fake_provider import (
    FakeAthensV2,
    FakeMumbaiV2,
    FakePerth,
    FakePrague,
    FakeProviderForBackendV2,
    FakeSherbrooke,
    fake_backend,
)
from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2

from ...ibm_test_case import IBMTestCase

FAKE_PROVIDER_FOR_BACKEND_V2 = FakeProviderForBackendV2()


def make_refresh_service(backend):
    """Build a mocked service that returns ``backend``'s own bundled data as the real data.

    This lets ``refresh`` run without any network access. A distinctive ``backend_version`` is
    injected so tests can assert the in-session update actually took effect.
    """
    real_config = backend.configuration()
    real_config.backend_version = "9.9.9-refreshed"
    real_props = backend.properties()

    fake_real_backend = mock.MagicMock()
    fake_real_backend.properties.return_value = real_props
    service = mock.MagicMock(spec=QiskitRuntimeService)
    service.backends.return_value = [fake_real_backend]

    patcher = mock.patch.object(
        fake_backend, "configuration_from_server_data", return_value=real_config
    )
    return service, patcher


class FakeBackendsTest(IBMTestCase):
    """fake backends test."""

    @unittest.skipUnless(optionals.HAS_AER, "qiskit-aer is required to run this test")
    def test_fake_backends_get_kwargs(self):
        """Fake backends honor kwargs passed."""
        backend = FakeAthensV2()

        qc = QuantumCircuit(2)
        qc.x(range(0, 2))
        qc.measure_all()

        trans_qc = transpile(qc, backend)
        sampler = SamplerV2(backend)
        job = sampler.run([trans_qc])
        pub_result = job.result()[0]
        counts = pub_result.data.meas.get_counts()

        assert sum(counts.values()) == 1024

    @unittest.skipUnless(optionals.HAS_AER, "qiskit-aer is required to run this test")
    def test_fake_backend_v2_noise_model_always_present(self):
        """Test that FakeBackendV2 instances always run with noise."""
        backend = FakePerth()
        qc = QuantumCircuit(1)
        qc.x(0)
        qc.measure_all()
        sampler = SamplerV2(backend)
        job = sampler.run([qc])
        pub_result = job.result()[0]
        counts = pub_result.data.meas.get_counts()
        # Assert noise was present and result wasn't ideal
        assert counts != {"1": 1000}

    def test_retrieving_single_backend(self):
        """Test retrieving a single backend."""
        provider = FakeProviderForBackendV2()
        backend_name = "fake_jakarta"
        backend = provider.backend(backend_name)
        assert backend.name == backend_name

    def test_all_fake_backends_registered(self):
        """Test that every fake backend class in the module is registered in the provider."""
        all_classes = {
            name
            for name in dir(fake_provider)
            if name.startswith("Fake")
            and isinstance(getattr(fake_provider, name), type)
            and issubclass(getattr(fake_provider, name), FakeBackendV2)
        }
        registered = {type(backend).__name__ for backend in FakeProviderForBackendV2().backends()}
        assert all_classes == registered


class FakeBackendRefreshTest(IBMTestCase):
    """Tests for the ``persist`` behavior of :meth:`.FakeBackendV2.refresh`.

    With ``persist=False`` the refreshed data must be written to a temporary directory rather
    than into the installed package directory (often read-only, e.g. ``site-packages``), so that
    :meth:`~.FakeBackendV2.refresh` succeeds without modifying the installed package.
    """

    def test_refresh_no_persist_leaves_package_untouched(self):
        """``persist=False`` writes to a temp dir and never modifies the bundled files."""
        backend = FakeAthensV2()
        pkg_dir = backend.dirname
        pkg_conf = os.path.join(pkg_dir, backend.conf_filename)
        pkg_props = os.path.join(pkg_dir, backend.props_filename)
        pkg_conf_mtime = os.stat(pkg_conf).st_mtime_ns
        pkg_props_mtime = os.stat(pkg_props).st_mtime_ns

        service, patcher = make_refresh_service(backend)
        with patcher:
            with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
                backend.refresh(service, persist=False)

        assert "has been updated" in "".join(logs.output)

        # ``dirname`` is left untouched (still pointing at the bundled files).
        # The refreshed data is written to and read from the temporary directory instead.
        assert backend.dirname == pkg_dir
        assert backend._tmp_data_dir is not None
        tmp_dir = backend._tmp_data_dir.name
        assert tmp_dir != pkg_dir
        assert os.path.exists(os.path.join(tmp_dir, backend.conf_filename))
        assert os.path.exists(os.path.join(tmp_dir, backend.props_filename))

        # The backend was updated in-session.
        assert backend._conf_dict["backend_version"] == "9.9.9-refreshed"

        # The bundled package files must remain untouched.
        assert os.stat(pkg_conf).st_mtime_ns == pkg_conf_mtime
        assert os.stat(pkg_props).st_mtime_ns == pkg_props_mtime

    def test_refresh_persist_after_no_persist_targets_bundled_files(self):
        """A ``persist=True`` ``refresh()`` after a ``persist=False`` one still targets ``dirname``.

        Since ``persist=False`` no longer overwrites ``dirname``, a subsequent persisting
        ``refresh()`` writes back into the (writable copy of the) bundled directory as expected.
        """
        backend = FakeAthensV2()
        with tempfile.TemporaryDirectory() as data_dir:
            shutil.copy(os.path.join(backend.dirname, backend.conf_filename), data_dir)
            shutil.copy(os.path.join(backend.dirname, backend.props_filename), data_dir)
            backend.dirname = data_dir

            service, patcher = make_refresh_service(backend)
            with patcher:
                backend.refresh(service, persist=False)
                assert backend._tmp_data_dir is not None

                backend.refresh(service)

            # The in-place refresh writes back into ``dirname`` (the writable copy).
            assert backend.dirname == data_dir
            reloaded = FakeAthensV2()
            reloaded.dirname = data_dir
            reloaded._conf_dict = reloaded._get_conf_dict_from_json()
            assert reloaded._conf_dict["backend_version"] == "9.9.9-refreshed"

    def test_refresh_default_writes_in_place(self):
        """The default (``persist=True``) writes back into ``dirname`` without a temp dir.

        ``dirname`` is redirected to a writable copy of the bundled data so the test never touches
        the real installed package files.
        """
        backend = FakeAthensV2()
        with tempfile.TemporaryDirectory() as data_dir:
            shutil.copy(os.path.join(backend.dirname, backend.conf_filename), data_dir)
            shutil.copy(os.path.join(backend.dirname, backend.props_filename), data_dir)
            backend.dirname = data_dir

            service, patcher = make_refresh_service(backend)
            with patcher:
                with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
                    backend.refresh(service)

            assert "has been updated" in "".join(logs.output)

            # No temporary directory is created and ``dirname`` is unchanged.
            assert backend.dirname == data_dir
            assert backend._tmp_data_dir is None

            # The in-place data file was overwritten with the refreshed data, and a freshly
            # constructed backend pointed at the same directory picks up the update.
            reloaded = FakeAthensV2()
            reloaded.dirname = data_dir
            reloaded._conf_dict = reloaded._get_conf_dict_from_json()
            assert reloaded._conf_dict["backend_version"] == "9.9.9-refreshed"
            assert backend._conf_dict["backend_version"] == "9.9.9-refreshed"


@ddt
class TestFakeBackends(IBMTestCase):
    """Test case for fake backends."""

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_to_dict_properties(self, backend):
        """Test converting backend properties to dict."""
        properties = backend.properties()
        if properties:
            assert isinstance(backend.properties().to_dict(), dict)
        else:
            assert backend.configuration().simulator

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_convert_to_target(self, backend):
        """Test backend target's dt."""
        target = backend.target
        if target.dt is not None:
            assert target.dt < 1e-6

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_backend_v2_dtm(self, backend):
        """Test backend dtm"."""
        if backend.dtm:
            assert backend.dtm < 1e-6

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_to_dict_configuration(self, backend):
        """Test backend configuration."""
        configuration = backend.configuration()
        if configuration.open_pulse:
            assert configuration.dt < 1e-6
            assert configuration.dtm < 1e-6
            for i in configuration.qubit_lo_range:
                assert i[0] > 1e6
                assert i[1] > 1e6
                assert i[0] < i[1]

            for i in configuration.meas_lo_range:
                assert i[0] > 1e6
                assert i[0] > 1e6
                assert i[0] < i[1]

            for i in configuration.rep_times:
                assert i > 0
                assert i < 1

        assert isinstance(configuration.to_dict(), dict)
        # test unit/value consistency on roundtrip
        if hasattr(configuration, "rep_times"):
            config_dict = configuration.to_dict()
            roundtrip_config = configuration.from_dict(config_dict)
            assert configuration.rep_times == roundtrip_config.rep_times

    def test_delay_circuit(self):
        """Test transpiling with delay."""
        backend = FakeMumbaiV2()
        qc = QuantumCircuit(2)
        qc.delay(502, 0, unit="ns")
        qc.x(1)
        qc.delay(250, 1, unit="ns")
        qc.measure_all()
        res = transpile(qc, backend)
        assert "delay" in res.count_ops()

    def test_non_cx_tests(self):
        """Test using non cx gates."""
        backend = FakePrague()
        assert isinstance(backend.target.operation_from_name("cz"), CZGate)
        backend = FakeSherbrooke()
        assert isinstance(backend.target.operation_from_name("ecr"), ECRGate)

    def test_backend_configuration_attributes(self):
        """Test specific backend configuration attributes."""
        backend = FakeMumbaiV2()
        assert backend.dynamic_reprate_enabled
        assert backend.rep_delay_range

    @data(*FAKE_PROVIDER_FOR_BACKEND_V2.backends())
    def test_backend_physical_qubits(self, backend):
        """Test the `physical_qubits` property of backends.

        `physical_qubits` was added to all the backends that were active at the time.
        """
        backends_with_physical_qubits = [
            "fake_aachen",
            "fake_berlin",
            "fake_boston",
            "fake_fez",
            "fake_kingston",
            "fake_marrakesh",
            "fake_miami",
            "fake_pittsburgh",
        ]

        if backend.name in backends_with_physical_qubits:
            assert isinstance(backend.physical_qubits, int)
        else:
            assert backend.physical_qubits is None
