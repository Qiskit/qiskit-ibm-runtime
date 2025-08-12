# This code is part of Qiskit.
#
# (C) Copyright IBM 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Fake Fractional device (5 qubit).
"""

import os
from qiskit_ibm_runtime.fake_provider import fake_backend


class FakeFractionalBackend(fake_backend.FakeBackendV2):
    """A fake 5 qubit backend with dynamic and fractional feature modeled based on FakeLima.

    This backend include following features.

    * Fractional gates (rx, rzx) in addition to the standard basis gates.
    * Control flow operations (if_else, while_loop).
    * Pulse calibrations (fractional gates don't support calibration).
    * Gate properties of all instructions.
    """

    dirname = os.path.dirname(__file__)  # type: ignore
    conf_filename = "conf_fractional.json"  # type: ignore
    props_filename = "props_fractional.json"  # type: ignore
    backend_name = "fake_fractional"  # type: ignore
