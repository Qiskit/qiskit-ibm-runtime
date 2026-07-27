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
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_authentication
from ..ibm_test_case import IBMTestCase
from ..registries import Backend, Instance, OneInstanceNoBackendsRegistry
from ..utils import transpile_pubs


class TestQiskitRuntimeService(IBMTestCase):
    """Class for testing the `QiskitRuntimeService` class."""

    @mock_authentication(OneInstanceNoBackendsRegistry)
    def test_run_active_client(self, registry):
        """`_run()` should use the backend/instance api client rather than the active client."""
        # Create several instances, with one instance per backend, so they use different clients.
        registry.add_instance(Instance("b"))
        registry.add_instance(Instance("c"))
        registry.add_backend(Backend("backend_a"), "a")
        registry.add_backend(Backend("backend_b"), "b")
        registry.add_backend(Backend("backend_c"), "c")

        # Retrieve backends
        service = QiskitRuntimeService(token="token")
        backend_a, backend_b, backend_c = service.backends()
        # Mimic that backend_c is not available in the service.
        backend_c._instance = "invalid"

        # Add mocks in order to ensure which clients are used.
        backend_a._api_client.program_run = MagicMock(wraps=backend_a._api_client.program_run)
        backend_b._api_client.program_run = MagicMock(wraps=backend_b._api_client.program_run)
        backend_c._api_client.program_run = MagicMock(wraps=backend_c._api_client.program_run)

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
