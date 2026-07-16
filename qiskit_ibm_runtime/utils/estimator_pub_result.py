# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""EstimatorPubResult result classes."""

import warnings

from ..results import EstimatorPubResult  # noqa: F401

warnings.warn(
    "The `EstimatorPubResult` class has been moved to the `qiskit_ibm_runtime.results` package as "
    "of qiskit_ibm_runtime v0.48.0, and it will be its only location in a future release, 3 months"
    "or more after v0.48.0. Please adjust your imports accordingly.",
    DeprecationWarning,
    stacklevel=2,
)
