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

from typing import Annotated, Literal

from pydantic import AfterValidator

from ..utils.deprecation import issue_deprecation_msg
from .base import BaseOptionsModel


def _warn_post_selection(value: bool) -> bool:
    """Warn that the post selection options are deprecated."""
    if value:
        issue_deprecation_msg(
            msg="The 'post_selection' field of NoiseLearnerV3 is deprecated",
            version="0.49.0",
            remedy="Use 'bit_flip_check' field instead",
            stacklevel=2,
        )
    return value


class PostSelectionOptions(BaseOptionsModel):
    """Options for post selecting results."""

    enable: Annotated[bool, AfterValidator(_warn_post_selection)] = False
    """Whether to enable Post Selection when performing learning experiments.

    If ``True``, Post Selection is applied to all the learning circuits. In particular, the
    following steps are undertaken:

    * Using the passes in
        :mod:`qiskit_addon_utils.noise_management.post_selection.transpiler.passes`, the learning
        circuits are modified by adding measurements on the spectator qubits, as well as
        post selection measurements.
    * The results of each individual learning circuits are post selected by discarding the shots
        where one or more bits failed to flip, as explained in the docstring of
        :meth:`qiskit_addon_utils.noise_management.post_selection.PostSelector.compute_mask`.

    If ``False``, all the other Post Selection options will be ignored.
    """

    x_pulse_type: Literal["xslow", "rx"] = "xslow"
    """The type of the X-pulse used for the post selection measurements."""

    strategy: Literal["node", "edge"] = "node"
    """The strategy used to decide if a shot should be kept or discarded.

    The available startegies are:

    * ``'node'``: Discard every shot where one or more bits failed to flip. Keep every other shot.
    * ``'edge'``: Discard every shot where there exists a pair of neighbouring qubits for which
        both of the bits failed to flip. Keep every other shot.

    See the dosctrings of :class:`.PostSelector` and :meth:`.PostSelector.compute_mask` for more
    details.
    """
