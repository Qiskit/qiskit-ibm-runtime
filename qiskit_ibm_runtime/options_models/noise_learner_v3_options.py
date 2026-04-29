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

"""NoiseLearnerV3Options options."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field
from pydantic.dataclasses import dataclass

from .environment_options import EnvironmentOptions
from .execution_options import ExecutionOptions
from .post_selection_options import PostSelectionOptions
from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class NoiseLearnerV3Options:
    """Options for :class:`.NoiseLearnerV3`."""

    shots_per_randomization: Annotated[int, Field(ge=1)] = 128
    """The total number of shots to use per randomized learning circuit."""

    num_randomizations: Annotated[int, Field(ge=1)] = 32
    """The number of random circuits to use per learning circuit configuration.

    For TREX experiments, a configuration is a measurement basis.

    For Pauli Lindblad experiments, a configuration is a measurement basis and depth setting.
    For example, if your experiment has six depths, then setting this value to ``32`` will result
    in a total of ``32 * 9 * 6`` circuits that need to be executed (where ``9`` is the number
    of circuits that need to be implemented to measure all the required observables, see the
    note in the docstring for :class:`~.NoiseLearnerOptions` for mode details), at
    :attr:`~shots_per_randomization` each.
    """

    layer_pair_depths: list[Annotated[int, Field(ge=0)]] = (0, 1, 2, 4, 16, 32)  # type: ignore[assignment]
    """The circuit depths (measured in number of pairs) to use in Pauli Lindblad experiments.

    Pairs are used as the unit because we exploit the order-2 nature of our entangling gates in
    the noise learning implementation. For example, a value of ``3`` corresponds to 6 repetitions
    of the layer of interest.

    .. note::
        This field is ignored by TREX experiments.
    """

    post_selection: PostSelectionOptions = Field(default_factory=PostSelectionOptions)
    """Options for post selecting the results of noise learning circuits.
    """

    experimental: dict = Field(default_factory=dict)
    """Experimental options.

    These options are subject to change without notification, and stability is not guaranteed.
    """

    execution: ExecutionOptions = Field(default_factory=ExecutionOptions)
    """Low-level execution options."""

    environment: EnvironmentOptions = Field(default_factory=EnvironmentOptions)
    """Options related to the execution environment."""
