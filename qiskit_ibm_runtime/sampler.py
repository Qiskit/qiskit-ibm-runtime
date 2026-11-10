# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Sampler primitive."""

import warnings

from .server_side import Sampler, SamplerV2  # noqa: F401

warnings.warn(
    "You are using a non-public import that will be removed in v0.53.0. Please adjust your imports "
    "accordingly, to either `from qiskit_ibm_runtime import Sampler` for using the client-side "
    "primitive or `from qiskit_ibm_runtime.server_side import Sampler` for using the server-side "
    "primitive.",
    DeprecationWarning,
    stacklevel=2,
)
