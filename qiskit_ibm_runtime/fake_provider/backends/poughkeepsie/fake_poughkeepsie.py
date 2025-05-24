# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Fake Poughkeepsie device (20 qubit).
"""

import os

from qiskit_ibm_runtime.fake_provider import fake_backend


class FakePoughkeepsieV2(fake_backend.FakeBackendV2):
    """A fake Poughkeepsie backend."""

    dirname = os.path.dirname(__file__)  # type: ignore
    conf_filename = "conf_poughkeepsie.json"  # type: ignore
    props_filename = "props_poughkeepsie.json"  # type: ignore
    backend_name = "fake_poughkeepsie"  # type: ignore
