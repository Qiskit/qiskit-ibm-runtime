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

from typing import Union

import numpy as np

from pydantic import BaseModel, ConfigDict


class Distribute(list):
    """Define a distribution of options values across PUBs."""

    def __init__(self, *args):
        super().__init__(args)

    def __repr__(self):
        return f"Distribute({', '.join(map(str, self))})"


NumArrayType = Union[int, np.ndarray[tuple[int, ...], np.dtype[np.uint64]]]
DistributableNumType = Union[NumArrayType, Distribute[NumArrayType]]


def get_value_for_pub_and_param(
    pub_index: int, param_index: Union[int, tuple], values_structure: DistributableNumType
) -> int:
    """Get the option value for the given PUB and parameter values"""
    internal_structure = values_structure
    if isinstance(internal_structure, Distribute):
        internal_structure = internal_structure[pub_index]
    if isinstance(internal_structure, np.ndarray):
        internal_structure = internal_structure[param_index]

    # internal_structure is certainly an integer now
    return internal_structure


class PrimitiveOptionsModel(BaseModel):
    """Pydantic model of Primitive options."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    seed: DistributableNumType
    experimental: dict
