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

"""Utility functions for the runtime service."""

import warnings

from ..json import (  # noqa: F401
    CURRENT_NOISE_LEARNER_MODULE,
    LEGACY_NOISE_LEARNER_MODULE,
    SERVICE_MAX_SUPPORTED_QPY_VERSION,
    RuntimeDecoder,
    RuntimeEncoder,
    _cast_strings_keys_to_int,
    _decode_and_deserialize,
    _deserialize_from_json,
    _deserialize_from_settings,
    _serialize_and_encode,
    _set_int_keys_flag,
    to_base64_string,
)

warnings.warn(
    "The `qiskit_ibm_runtime.utils.json` package has been moved to `qiskit_ibm_runtime.json` as "
    "of qiskit_ibm_runtime v0.48.0, and it will be its only location in a future release, 3 months "
    "or more after v0.48.0. Please adjust your imports accordingly, and note that the only public "
    "items are `RuntimeDecoder` and `RuntimeEncoder`, which are available as top-level imports.",
    DeprecationWarning,
    stacklevel=2,
)
