# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
# type: ignore

"""Primitive abstract base class."""

from __future__ import annotations
from typing import Optional

from abc import ABC

from .options import BasePrimitiveOptions, BasePrimitiveOptionsLike


class BasePrimitiveV2(ABC):
    """Primitive abstract base class."""

    version = 2
    _options_class: type[BasePrimitiveOptions] = BasePrimitiveOptions

    def __init__(self, options: Optional[BasePrimitiveOptionsLike] = None):
        self._options: type(self)._options_class
        self._set_options(options)

    @property
    def options(self) -> BasePrimitiveOptions:
        """Options for BaseEstimator"""
        return self._options

    @options.setter
    def options(self, options: BasePrimitiveOptionsLike) -> None:
        self._set_options(options)

    def _set_options(self, options):
        if options is None:
            self._options = self._options_class()
        elif isinstance(options, dict):
            self._options = self._options_class(**options)
        elif isinstance(options, self._options_class):
            self._options = options
        else:
            raise TypeError(
                f"Invalid 'options' type. It can only be a dictionary of {self._options_class}"
            )
