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

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from ddt import data, ddt
from qiskit import QuantumCircuit

from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.exceptions import IBMRuntimeError
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..account import custom_envs
from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..registries import Backend, DefaultRegistry, Instance, OneInstanceNoBackendsRegistry
from ..utils import transpile_pubs

if TYPE_CHECKING:
    from ..registries import DefaultRegistry


@ddt
class TestQiskitRuntimeService(IBMTestCase):
    """Class for testing the `QiskitRuntimeService` class."""

    @mock_responses(OneInstanceNoBackendsRegistry)
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

    @mock_responses
    def test_initialization_state(self, registry: DefaultRegistry) -> None:
        """Test `__init__` state variables, with default arguments."""
        crns_in_registry = {instance.crn for instance in registry.instances.values()}
        backends_in_registry = {
            instance.crn: set(registry.backends[instance.name])
            for instance in registry.instances.values()
        }

        service = QiskitRuntimeService(token="my_token")
        # `_all_instances` contains all the instances available.
        self.assertEqual({instance["crn"] for instance in service._all_instances}, crns_in_registry)
        # `_backend_configs` is empty (populated by `backends()`).
        self.assertEqual(service._backend_configs, {})
        # `_api_clients` contains one client per instance available.
        self.assertEqual(set(service._api_clients.keys()), crns_in_registry)
        # `_active_api_client` is among the ones in `_api_clients`.
        self.assertIn(service._active_api_client, service._api_clients.values())
        # `_backends_info_per_instance` contains one entry per instance, with its backends.
        self.assertEqual(
            {
                crn: {info["name"] for info in value}
                for crn, value in service._backends_info_per_instance.items()
            },
            backends_in_registry,
        )
        # `_backend_instance_groups` contains one entry per instance, with its backends.
        self.assertEqual(
            {info["crn"]: set(info["backends"]) for info in service._backend_instance_groups},
            backends_in_registry,
        )

    @mock_responses(OneInstanceNoBackendsRegistry)
    @data(True, False)
    def test_initialization_state_passing_instance(
        self, with_env_var: bool, registry: OneInstanceNoBackendsRegistry
    ) -> None:
        """Test `__init__` state variables, passing the `instance` argument."""
        chosen_crn = registry.instances["a"].crn
        crns_in_registry = {chosen_crn}

        if with_env_var:
            # Using the `QISKIT_FUNCTIONS_EXPERIMENTAL` should have no side effects.
            with custom_envs({"QISKIT_FUNCTIONS_EXPERIMENTAL": "FOO"}):
                service = QiskitRuntimeService(token="my_token", instance=chosen_crn)
        else:
            service = QiskitRuntimeService(token="my_token", instance=chosen_crn)

        # `_all_instances` contains all the instances available.
        self.assertEqual({instance["crn"] for instance in service._all_instances}, crns_in_registry)
        # `_backend_configs` is empty (populated by `backends()`).
        self.assertEqual(service._backend_configs, {})
        # `_api_clients` contains only a client for the specified instance.
        self.assertEqual(set(service._api_clients.keys()), {chosen_crn})
        # `_active_api_client` is among the ones in `_api_clients`.
        self.assertIn(service._active_api_client, service._api_clients.values())
        # `_backends_info_per_instance` is empty.
        self.assertEqual(service._backends_info_per_instance, {})
        # `_backend_instance_groups` is empty.
        self.assertEqual(service._backend_instance_groups, [])
