# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Jupyter tools."""

from qiskit_ibm_runtime.jupyter.qubits_widget import qubits_tab
from qiskit_ibm_runtime.jupyter.config_widget import config_tab
from qiskit_ibm_runtime.jupyter.gates_widget import gates_tab
from qiskit_ibm_runtime.visualization.interactive.error_map import iplot_error_map
from qiskit_ibm_runtime.jupyter.dashboard.backend_widget import make_backend_widget
from qiskit_ibm_runtime.jupyter.dashboard.utils import BackendWithProviders

from ..decorators import requires_provider
from ..ibm_test_case import IBMTestCase


class TestBackendInfo(IBMTestCase):
    """Test backend information Jupyter widget."""

    @classmethod
    @requires_provider
    def setUpClass(cls, service, hub, group, project):
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.hub = hub
        cls.group = group
        cls.project = project
        cls.backends = _get_backends(service)

    def test_config_tab(self):
        """Test config tab."""
        for backend in self.backends:
            with self.subTest(backend=backend):
                tab_str = str(config_tab(backend))
                config = backend.configuration()
                status = backend.status()
                self.assertIn(config.backend_name, tab_str)
                self.assertIn(str(status.status_msg), tab_str)

    def test_qubits_tab(self):
        """Test qubits tab."""
        for backend in self.backends:
            with self.subTest(backend=backend):
                tab_str = str(qubits_tab(backend))
                props = backend.properties().to_dict()
                q0_t1 = round(props['qubits'][0][0]['value'], 3)
                q0_t2 = round(props['qubits'][0][1]['value'], 3)
                self.assertIn(str(q0_t1), tab_str)
                self.assertIn(str(q0_t2), tab_str)

    def test_gates_tab(self):
        """Test gates tab."""
        for backend in self.backends:
            with self.subTest(backend=backend):
                gates_tab(backend)

    def test_error_map_tab(self):
        """Test error map tab."""
        for backend in self.backends:
            with self.subTest(backend=backend):
                iplot_error_map(backend)


class TestIBMDashboard(IBMTestCase):
    """Test backend information Jupyter widget."""

    @classmethod
    @requires_provider
    def setUpClass(cls, service, hub, group, project):
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.service = service
        cls.hub = hub
        cls.group = group
        cls.project = project
        cls.backends = _get_backends(service)

    def test_backend_widget(self):
        """Test devices tab."""
        for backend in self.backends:
            with self.subTest(backend=backend):
                provider_str = "{}/{}/{}".format(backend.hub, backend.group, backend.project)
                b_w_p = BackendWithProviders(backend=backend, providers=[provider_str])
                make_backend_widget(b_w_p)


def _get_backends(service):
    """Return backends for testing."""
    backends = []
    n_qubits = [1, 5]
    for n_qb in n_qubits:
        filtered_backends = service.backends(
            operational=True, simulator=False, n_qubits=n_qb)
        if filtered_backends:
            backends.append(filtered_backends[0])
    return backends
