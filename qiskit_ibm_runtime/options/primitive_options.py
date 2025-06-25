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

from .primitive_options_model import PrimitiveOptionsModel, SeedType, DistributableNumType


class PrimitiveOptions:
    """Primitive options."""

    def __init__(self, seed: DistributableNumType):
        self._model = PrimitiveOptionsModel(seed=seed)

    @property
    def seed(self) -> DistributableNumType:
        """Return the seed"""
        return self._model.seed
