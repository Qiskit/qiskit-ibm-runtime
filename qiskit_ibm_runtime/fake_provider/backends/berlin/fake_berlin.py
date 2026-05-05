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

"""Fake Berlin device (120 qubit)."""

import os

from qiskit_ibm_runtime.fake_provider import fake_backend


class FakeBerlin(fake_backend.FakeBackendV2):
    """A fake 120 qubit backend."""

    dirname = os.path.dirname(__file__)
    conf_filename = "conf_berlin.json"
    props_filename = "props_berlin.json"
    backend_name = "fake_berlin"
