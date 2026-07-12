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

import math
import os
import shutil
import tempfile
import unittest
from unittest import mock

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.utils import optionals

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.fake_provider import (
    FakeAthensV2,
    FakePerth,
    FakeProviderForBackendV2,
    fake_backend,
)

from ...ibm_test_case import IBMTestCase


def get_test_circuit():
    """Generates simple circuit for tests."""
    desired_vector = [1 / math.sqrt(2), 0, 0, 1 / math.sqrt(2)]
    qreg = QuantumRegister(2, "qr")
    creg = ClassicalRegister(2, "cr")
    qc = QuantumCircuit(qreg, creg)
    qc.initialize(desired_vector, [qreg[0], qreg[1]])
    qc.measure(qreg[0], creg[0])
    qc.measure(qreg[1], creg[1])
    return qc


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

        self.assertEqual(sum(counts.values()), 1024)

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
        self.assertNotEqual(counts, {"1": 1000})

    def test_retrieving_single_backend(self):
        """Test retrieving a single backend."""
        provider = FakeProviderForBackendV2()
        backend_name = "fake_jakarta"
        backend = provider.backend(backend_name)
        self.assertEqual(backend.name, backend_name)


class FakeBackendRefreshTest(IBMTestCase):
    """Tests for the ``persist`` behavior of :meth:`.FakeBackendV2.refresh`.

    With ``persist=False`` the refreshed data must be written to a temporary directory rather
    than into the installed package directory (often read-only, e.g. ``site-packages``), so that
    :meth:`~.FakeBackendV2.refresh` succeeds without modifying the installed package.
    """

    def _make_refresh_service(self, backend):
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

    def test_refresh_no_persist_leaves_package_untouched(self):
        """``persist=False`` writes to a temp dir and never modifies the bundled files."""
        backend = FakeAthensV2()
        pkg_dir = backend.dirname
        pkg_conf = os.path.join(pkg_dir, backend.conf_filename)
        pkg_props = os.path.join(pkg_dir, backend.props_filename)
        pkg_conf_mtime = os.stat(pkg_conf).st_mtime_ns
        pkg_props_mtime = os.stat(pkg_props).st_mtime_ns

        service, patcher = self._make_refresh_service(backend)
        with patcher:
            with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
                backend.refresh(service, persist=False)

        self.assertIn("has been updated", "".join(logs.output))

        # ``dirname`` is left untouched (still pointing at the bundled files).
        # The refreshed data is written to and read from the temporary directory instead.
        self.assertEqual(backend.dirname, pkg_dir)
        self.assertIsNotNone(backend._tmp_data_dir)
        tmp_dir = backend._tmp_data_dir.name
        self.assertNotEqual(tmp_dir, pkg_dir)
        self.assertTrue(os.path.exists(os.path.join(tmp_dir, backend.conf_filename)))
        self.assertTrue(os.path.exists(os.path.join(tmp_dir, backend.props_filename)))

        # The backend was updated in-session.
        self.assertEqual(backend._conf_dict["backend_version"], "9.9.9-refreshed")

        # The bundled package files must remain untouched.
        self.assertEqual(os.stat(pkg_conf).st_mtime_ns, pkg_conf_mtime)
        self.assertEqual(os.stat(pkg_props).st_mtime_ns, pkg_props_mtime)

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

            service, patcher = self._make_refresh_service(backend)
            with patcher:
                backend.refresh(service, persist=False)
                self.assertIsNotNone(backend._tmp_data_dir)

                backend.refresh(service)

            # The in-place refresh writes back into ``dirname`` (the writable copy).
            self.assertEqual(backend.dirname, data_dir)
            reloaded = FakeAthensV2()
            reloaded.dirname = data_dir
            reloaded._conf_dict = reloaded._get_conf_dict_from_json()
            self.assertEqual(reloaded._conf_dict["backend_version"], "9.9.9-refreshed")

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

            service, patcher = self._make_refresh_service(backend)
            with patcher:
                with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
                    backend.refresh(service)

            self.assertIn("has been updated", "".join(logs.output))

            # No temporary directory is created and ``dirname`` is unchanged.
            self.assertEqual(backend.dirname, data_dir)
            self.assertIsNone(backend._tmp_data_dir)

            # The in-place data file was overwritten with the refreshed data, and a freshly
            # constructed backend pointed at the same directory picks up the update.
            reloaded = FakeAthensV2()
            reloaded.dirname = data_dir
            reloaded._conf_dict = reloaded._get_conf_dict_from_json()
            self.assertEqual(reloaded._conf_dict["backend_version"], "9.9.9-refreshed")
            self.assertEqual(backend._conf_dict["backend_version"], "9.9.9-refreshed")
