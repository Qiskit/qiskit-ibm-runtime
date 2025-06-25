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

"""Pydantic model of Primitive options."""

import numpy as np

from pydantic import BaseModel, ConfigDict


class Distribute(list):
    def __init__(self, *args):
        super().__init__(args)

    def __repr__(self):
        return f"Distribute({', '.join(map(str, self))})"


SeedType = int | np.ndarray[tuple[int, ...], np.dtype[np.uint64]]


class PrimitiveOptionsModel(BaseModel):
    """Pydantic model of Primitive options."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    seed: SeedType | Distribute[SeedType]
