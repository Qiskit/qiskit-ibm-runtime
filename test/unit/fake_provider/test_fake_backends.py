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

import json
import math
import os
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
)
from qiskit_ibm_runtime.fake_provider import fake_backend

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


class FakeBackendDataCacheTest(IBMTestCase):
    """Tests for the local caching of refreshed fake backend data.

    These guard against regressing the behavior where :meth:`.FakeBackendV2.refresh` must not
    write into the installed package directory (often read-only, e.g. ``site-packages``) and
    instead caches data under the user-writable ``~/.qiskit`` directory.
    """

    def test_resolve_data_path_without_cache_uses_bundled(self):
        """Without a cached copy, data files resolve to the bundled package location."""
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                fake_backend, "_LOCAL_DATA_DIR", os.path.join(tmp, "fp")
            ):
                backend = FakeAthensV2()
                self.assertEqual(
                    backend._resolve_data_path(backend.conf_filename),
                    os.path.join(backend.dirname, backend.conf_filename),
                )

    def test_cached_data_takes_precedence_over_bundled(self):
        """A cached copy in the local data dir is loaded in preference to the bundled file."""
        with tempfile.TemporaryDirectory() as tmp:
            local_root = os.path.join(tmp, "fp")
            with mock.patch.object(fake_backend, "_LOCAL_DATA_DIR", local_root):
                backend = FakeAthensV2()
                conf = backend._load_json(backend.conf_filename)
                conf["backend_version"] = "9.9.9-cached"

                local_dir = os.path.join(local_root, backend.backend_name)
                os.makedirs(local_dir)
                with open(
                    os.path.join(local_dir, backend.conf_filename),
                    "w",
                    encoding="utf-8",
                ) as fd:
                    json.dump(conf, fd)

                # A freshly constructed backend should pick up the cached data.
                cached_backend = FakeAthensV2()
                self.assertEqual(
                    cached_backend._resolve_data_path(cached_backend.conf_filename),
                    os.path.join(local_dir, cached_backend.conf_filename),
                )
                self.assertEqual(
                    cached_backend._conf_dict["backend_version"], "9.9.9-cached"
                )

    def test_refresh_writes_to_local_cache_not_package(self):
        """refresh() writes data to the local cache dir and leaves the package files untouched."""
        with tempfile.TemporaryDirectory() as tmp:
            local_root = os.path.join(tmp, "fp")
            with mock.patch.object(fake_backend, "_LOCAL_DATA_DIR", local_root):
                backend = FakeAthensV2()

                # Reuse the bundled data to stand in for the "real" backend response, so the test
                # needs no network access.
                real_config = backend.configuration()
                real_props = backend.properties()

                # Snapshot the bundled files so we can assert they are never modified.
                pkg_conf = os.path.join(backend.dirname, backend.conf_filename)
                pkg_props = os.path.join(backend.dirname, backend.props_filename)
                pkg_conf_before = (pkg_conf, os.stat(pkg_conf).st_mtime_ns)
                pkg_props_before = (pkg_props, os.stat(pkg_props).st_mtime_ns)

                fake_real_backend = mock.MagicMock()
                fake_real_backend.properties.return_value = real_props
                service = mock.MagicMock(spec=QiskitRuntimeService)
                service.backends.return_value = [fake_real_backend]

                with mock.patch.object(
                    fake_backend,
                    "configuration_from_server_data",
                    return_value=real_config,
                ):
                    with self.assertLogs("qiskit_ibm_runtime", level="INFO") as logs:
                        backend.refresh(service)

                self.assertIn("has been updated", "".join(logs.output))

                local_dir = os.path.join(local_root, backend.backend_name)
                self.assertTrue(
                    os.path.exists(os.path.join(local_dir, backend.conf_filename))
                )
                self.assertTrue(
                    os.path.exists(os.path.join(local_dir, backend.props_filename))
                )

                # The bundled package files must remain untouched.
                self.assertEqual(os.stat(pkg_conf).st_mtime_ns, pkg_conf_before[1])
                self.assertEqual(os.stat(pkg_props).st_mtime_ns, pkg_props_before[1])
