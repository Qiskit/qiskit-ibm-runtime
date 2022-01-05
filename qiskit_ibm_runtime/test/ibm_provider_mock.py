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

"""Mock for qiskit_ibm_runtime.IBMRuntimeService."""

from unittest.mock import MagicMock
from qiskit.test import mock as backend_mocks
import qiskit_ibm_runtime


def mock_get_backend(backend):
    """Replace qiskit_ibm_runtime.IBMRuntimeService with a mock that returns a single backend.
    Note this will set the value of qiskit_ibm_runtime.IBMRuntimeService to a MagicMock object. It
    is intended to be run as part of docstrings with jupyter-example in a hidden
    cell so that later examples which rely on ibm quantum devices so that the docs can
    be built without requiring configured accounts. If used outside of this
    context be aware that you will have to manually restore qiskit_ibm_runtime.IBMRuntimeService
    the value to qiskit_ibm_runtime.IBMRuntimeService after you finish using your mock.
    Args:
        backend (str): The class name as a string for the fake device to
            return. For example, FakeVigo.
    Raises:
        NameError: If the specified value of backend
    """
    mock_ibm_provider = MagicMock()
    if not hasattr(backend_mocks, backend):
        raise NameError(
            "The specified backend name is not a valid mock from qiskit.test.mock"
        )
    fake_backend = getattr(backend_mocks, backend)()
    mock_ibm_provider.get_backend.return_value = fake_backend
    mock_ibm_provider.return_value = mock_ibm_provider
    qiskit_ibm_runtime.IBMRuntimeService = mock_ibm_provider
