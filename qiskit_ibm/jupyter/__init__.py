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
"""
================================================================
Jupyter Tools (:mod:`qiskit_ibm.jupyter`)
================================================================

.. currentmodule:: qiskit_ibm.jupyter

A Collection of Jupyter magic functions and tools
that extend the functionality of Qiskit for the IBM
Quantum devices.

Note:
    To use these tools locally, you'll need to install the
    additional dependencies for the visualization functions::

        pip install qiskit_ibm[visualization]

Detailed information on a single backend
========================================

.. jupyter-execute::
    :hide-code:
    :hide-output:

    from qiskit_ibm.test.ibm_provider_mock import mock_get_backend
    mock_get_backend('FakeVigo')

.. jupyter-execute::

    from qiskit_ibm import IBMProvider
    import qiskit_ibm.jupyter

    provider = IBMProvider(hub='ibm-q')
    backend = provider.get_backend('ibmq_vigo')

.. jupyter-execute::
    :hide-code:
    :hide-output:

    backend.jobs = lambda *args, **kwargs: []

.. jupyter-execute::

    backend


IBM Quantum dashboard
======================================

.. code-block:: python

    from qiskit_ibm import IBMProvider
    import qiskit_ibm.jupyter

    %ibm_quantum_dashboard

"""
import sys

if ('ipykernel' in sys.modules) and ('spyder' not in sys.modules):

    from IPython import get_ipython          # pylint: disable=import-error
    from .dashboard.dashboard import IBMDashboardMagic
    from qiskit.test.mock import FakeBackend
    from ..ibm_backend import IBMBackend
    from .backend_info import backend_widget

    _IP = get_ipython()
    if _IP is not None:
        _IP.register_magics(IBMDashboardMagic)
        HTML_FORMATTER = _IP.display_formatter.formatters['text/html']
        # Make backend_widget the html repr for IBM Quantum backends
        HTML_FORMATTER.for_type(IBMBackend, backend_widget)
        HTML_FORMATTER.for_type(FakeBackend, backend_widget)
