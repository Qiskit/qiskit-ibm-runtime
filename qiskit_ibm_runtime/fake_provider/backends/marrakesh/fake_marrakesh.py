# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Fake Marrakesh device (156 qubit).
"""

import os
from qiskit_ibm_runtime.fake_provider import fake_backend


class FakeMarrakesh(fake_backend.FakeBackendV2):
    """A fake 156 qubit backend."""

    dirname = os.path.dirname(__file__)
    conf_filename = "conf_marrakesh.json"
    props_filename = "props_marrakesh.json"
    backend_name = "fake_marrakesh"
