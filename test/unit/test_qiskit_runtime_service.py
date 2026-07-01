# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for `QiskitRuntimeService`."""

from unittest.mock import MagicMock

from qiskit import QuantumCircuit

from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.exceptions import IBMRuntimeError

from ..decorators import run_cloud_fake
from ..ibm_test_case import IBMTestCase
from ..utils import transpile_pubs
from .mock.fake_api_backend import FakeApiBackendSpecs
from .mock.fake_runtime_client import BaseFakeRuntimeClient


class TestQiskitRuntimeService(IBMTestCase):
    """Class for testing the `QiskitRuntimeService` class."""

    @run_cloud_fake
    def test_run_active_client(self, service):
        """`_run()` should use the backend/instance api client rather than the active client."""
        # Prepare different backends.
        backend_a, backend_b, backend_c = service.backends()
        # A backend that has a client and instance registered and active in the service.
        backend_a._api_client.program_run = MagicMock(wraps=backend_a._api_client.program_run)
        # A backend that has a client and instance registered and not active in the service.
        backend_b._instance = "b"
        backend_b._api_client = BaseFakeRuntimeClient(
            instance="b", backend_specs=[FakeApiBackendSpecs(backend_b.name)]
        )
        backend_b._api_client.program_run = MagicMock(wraps=backend_b._api_client.program_run)
        # A backend that has a client and instance not registered in the service.
        backend_c._instance = "c"
        backend_c._api_client = BaseFakeRuntimeClient(
            instance="c", backend_specs=[FakeApiBackendSpecs(backend_c.name)]
        )
        backend_c._api_client.program_run = MagicMock(wraps=backend_c._api_client.program_run)

        # Prepare the service to mimic having multiple clients.
        service._api_clients = {
            backend_a._instance: backend_a._api_client,
            backend_b._instance: backend_b._api_client,
        }

        # Run a job with the client and instance active in the service.
        pubs = transpile_pubs([(QuantumCircuit(1),)], backend_a, "sampler")
        sampler = SamplerV2(mode=backend_a)
        _ = sampler.run(pubs)
        backend_a._api_client.program_run.assert_called()
        backend_b._api_client.program_run.assert_not_called()
        backend_c._api_client.program_run.assert_not_called()
        self.assertEqual(service._active_api_client, backend_a._api_client)
        backend_a._api_client.program_run.reset_mock()

        # Run a job with the client and instance not active in the service.
        sampler = SamplerV2(mode=backend_b)
        _ = sampler.run(pubs)
        backend_a._api_client.program_run.assert_not_called()
        backend_b._api_client.program_run.assert_called()
        backend_c._api_client.program_run.assert_not_called()
        self.assertEqual(service._active_api_client, backend_b._api_client)
        backend_b._api_client.program_run.reset_mock()

        # Run a job with the client and instance not active in the service.
        sampler = SamplerV2(mode=backend_c)
        with self.assertRaises(IBMRuntimeError) as ex:
            _ = sampler.run(pubs)
            self.assertIn("not among", str(ex.msg))

        backend_a._api_client.program_run.assert_not_called()
        backend_b._api_client.program_run.assert_not_called()
        backend_c._api_client.program_run.assert_not_called()
        self.assertEqual(service._active_api_client, backend_b._api_client)
