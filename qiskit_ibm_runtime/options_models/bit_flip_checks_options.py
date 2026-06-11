# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Post selection options."""

from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class PostCircuitBitFlipChecksOptions:
    """Options to apply post-circuit bit-flip checks to the results of noise learning circuits."""

    enable: bool = False
    """Whether to apply post-circuit bit-flip checks.

    If ``False``, all the other fields will be ignored.
    """

    x_pulse_type: Literal["xslow", "rx"] = "xslow"
    """The type of the X-pulse used for the post-circuit bit-flip checks."""

    strategy: Literal["node", "edge"] = "node"
    """The strategy used to decide if a shot should be kept or discarded.

    The available startegies are:

    * ``'node'``: Discard every shot where one or more bits failed to flip. Keep every other shot.
    * ``'edge'``: Discard every shot where there exists a pair of neighbouring qubits for which
      both of the bits failed to flip. Keep every other shot.
    """


@dataclass(config=PRIMITIVES_CONFIG)
class PreCircuitBitFlipChecksOptions:
    """Options to apply pre-circuit bit-flip checks to the results of noise learning circuits."""

    enable: bool = False
    """Whether to apply pre-circuit bit-flip checks.

    If ``False``, all the other fields will be ignored.
    """

    x_pulse_type: Literal["xslow", "rx"] = "xslow"
    """The type of the X-pulse used for the pre-circuit bit-flip checks."""

    strategy: Literal["node", "edge"] = "node"
    """The strategy used to decide if a shot should be kept or discarded.

    The available startegies are:

    * ``'node'``: Discard every shot where one or more bits failed to flip. Keep every other shot.
    * ``'edge'``: Discard every shot where there exists a pair of neighbouring qubits for which
      both of the bits failed to flip. Keep every other shot.
    """


@dataclass(config=PRIMITIVES_CONFIG)
class BitFlipChecksOptions:
    """Options to apply bit-flip checks to the results of noise learning circuits."""

    pre_circuit: PreCircuitBitFlipChecksOptions = Field(
        default_factory=PreCircuitBitFlipChecksOptions
    )
    """Options to apply pre-circuit bit-flip checks to the results of noise learning circuits."""

    post_circuit: PostCircuitBitFlipChecksOptions = Field(
        default_factory=PostCircuitBitFlipChecksOptions
    )
    """Options to apply post-circuit bit-flip checks to the results of noise learning circuits."""
