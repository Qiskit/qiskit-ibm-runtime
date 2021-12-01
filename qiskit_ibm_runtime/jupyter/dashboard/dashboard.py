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

"""The core IBM Quantum dashboard launcher."""

import threading
from typing import List, Dict, Any, Optional

import ipywidgets as wid
from IPython.display import display
from IPython.core.magic import line_magic, Magics, magics_class
from qiskit.tools.events.pubsub import Subscriber
from qiskit.exceptions import QiskitError

from ... import IBMRuntimeService
from .backend_widget import make_backend_widget
from .backend_update import update_backend_info
from .utils import BackendWithProviders


class AccordionWithThread(wid.Accordion):
    """An ``Accordion`` that will close an attached thread."""

    def __init__(self, children: Optional[List] = None, **kwargs: Any):
        """AccordionWithThread constructor.

        Args:
            children: A list of widgets to be attached to the accordion.
            **kwargs: Additional keywords to be passed to ``ipywidgets.Accordion``.
        """
        children = children or []
        super(AccordionWithThread, self).__init__(children=children, **kwargs)
        self._thread = None
        # Devices VBox.
        self._device_list = None  # type: Optional[wid.VBox]

    def __del__(self):
        """Object disposal."""
        if hasattr(self, "_thread"):
            try:
                self._thread.do_run = False
                self._thread.join()
            except Exception:  # pylint: disable=broad-except
                pass
        self.close()


def _add_device_to_list(backend: BackendWithProviders, device_list: wid.VBox) -> None:
    """Add the backend to the device list widget.

    Args:
        backend: Backend to add.
        device_list: Widget showing the devices.
    """
    device_pane = make_backend_widget(backend)
    device_list.children = list(device_list.children) + [device_pane]


class IBMDashboard(Subscriber):
    """An IBM Quantum dashboard.

    This dashboard shows both device and job information.
    """

    def __init__(self):
        """IBM Quantum Dashboard constructor."""
        super().__init__()

        self.service = None
        self.dashboard = None  # type: Optional[AccordionWithThread]

        # Backend dictionary. The keys are the backend names and the values
        # are named tuples of ``IBMBackend`` instances and a list of provider names.
        self.backend_dict = None  # type: Optional[Dict[str, BackendWithProviders]]

    def _get_backends(self) -> None:
        """Get all the backends accessible with this account."""

        ibm_backends = {}
        for pro in self.service._get_hgps():
            pro_name = "{hub}/{group}/{project}".format(
                hub=pro.credentials.hub,
                group=pro.credentials.group,
                project=pro.credentials.project,
            )
            for back in pro.backends():
                if not back.configuration().simulator:
                    if back.name() not in ibm_backends.keys():
                        ibm_backends[back.name()] = BackendWithProviders(
                            backend=back, providers=[pro_name]
                        )
                    else:
                        ibm_backends[back.name()].providers.append(pro_name)

        self.backend_dict = ibm_backends

    def refresh_device_list(self) -> None:
        """Refresh the list of devices."""
        for _wid in self.dashboard._device_list.children:
            _wid.close()
        self.dashboard._device_list.children = []
        for back in self.backend_dict.values():
            _thread = threading.Thread(
                target=_add_device_to_list, args=(back, self.dashboard._device_list)
            )
            _thread.start()

    def start_dashboard(self, service: IBMRuntimeService) -> None:
        """Starts the dashboard."""
        self.service = service
        self.dashboard = build_dashboard_widget()
        self._get_backends()
        self.refresh_device_list()
        self.dashboard._thread = threading.Thread(
            target=update_backend_info, args=(self.dashboard._device_list,)
        )
        self.dashboard._thread.do_run = True
        self.dashboard._thread.start()

    def stop_dashboard(self) -> None:
        """Stops the dashboard."""
        if self.dashboard:
            self.dashboard._thread.do_run = False
            self.dashboard._thread.join()
            self.dashboard.close()
        self.dashboard = None


def build_dashboard_widget() -> AccordionWithThread:
    """Build the dashboard widget.

    Returns:
        Dashboard widget.
    """
    tabs = wid.Tab(layout=wid.Layout(width="760px", max_height="650px"))

    devices = wid.VBox(children=[], layout=wid.Layout(width="740px", height="100%"))

    device_list = wid.Box(
        children=[devices], layout=wid.Layout(width="auto", max_height="600px")
    )

    tabs.children = [device_list]
    tabs.set_title(0, "Devices")

    acc = AccordionWithThread(
        children=[tabs],
        layout=wid.Layout(
            width="auto",
            max_height="700px",
        ),
    )

    acc._device_list = acc.children[0].children[0].children[0]

    acc.set_title(0, "IBM Quantum Dashboard")
    acc.selected_index = None
    acc.layout.visibility = "hidden"
    display(acc)
    acc.layout.visibility = "visible"
    return acc


@magics_class
class IBMDashboardMagic(Magics):
    """A class for enabling/disabling the IBM Quantum dashboard."""

    @line_magic
    def ibm_quantum_dashboard(self, line="", cell=None) -> None:
        """A Jupyter magic function to enable the dashboard."""
        # pylint: disable=unused-argument
        try:
            service = IBMRuntimeService(auth="legacy")
        except Exception:
            raise QiskitError("Could not load IBM Quantum account from the local file.")
        _IBM_DASHBOARD.stop_dashboard()
        _IBM_DASHBOARD.start_dashboard(service)

    @line_magic
    def disable_ibm_quantum_dashboard(self, line="", cell=None) -> None:
        """A Jupyter magic function to disable the dashboard."""
        # pylint: disable=unused-argument
        _IBM_DASHBOARD.stop_dashboard()


_IBM_DASHBOARD = IBMDashboard()
"""The Jupyter IBM Quantum dashboard instance."""
