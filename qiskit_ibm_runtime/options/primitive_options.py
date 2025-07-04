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

"""Primitive options."""

from typing import Literal

import numpy as np

from qiskit.quantum_info import PauliLindbladMap

from .distribute import Distribute
from .utils import primitive_dataclass

IntType = int | np.ndarray[tuple[int, ...]] | np.dtype[np.uint64]
NoiseRecordType = Literal["none", "parity", "sparse"]


@primitive_dataclass
class PrimitiveOptions:
    """Primitive options."""

    seed: IntType | Distribute[IntType]
    r"""The seed to use for randomization."""

    shots_per_randomization: IntType | Distribute[IntType]
    r"""The number of shots per randomization."""

    noise_models: dict[str, PauliLindbladMap] | None = None
    r"""A map from unique identifiers to noise models to apply to annotated boxes.

    Any box with an inject noise annotation with a matching identifier will draw samples from
    the map when generating randomizations for a PUB.
    """

    return_injection_record: NoiseRecordType | Distribute[NoiseRecordType] = "none"
    r"""Whether to return sign information when applying noise injection.
    
    The different values correspond to if any or how much information is returned:

        * If `"none"`, signs are not returned.
        * If `"parity"`, one sign is returned per pub element, equal to the parity of all signs 
          computed in that pub element. These signs are placed in an array
          `pub_result.data.injection_record`.
        * If `"sparse"`, signs are returned for all Lindblad terms in a sparse format. The 
          `injection_record` entry of `pub_result.data` is a `(num_negative, 3)`-shaped integer array
          where `pub_idx, lindblad_map_idx, term_idx = injection_record[i]` indicates the location of a
          negative value, and the rest are assumed to be positive.
    
    """

    experimental: dict | None = None
    r"""Experimental options."""
