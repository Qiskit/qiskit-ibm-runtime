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

"""Post selection options."""

from typing import Literal

from .options import BaseOptions
from .utils import primitive_dataclass

DEFAULT_X_PULSE_TYPE = "xslow"
"""The default for :meth:`.PostSelectionOptions.x_pulse_type`."""


@primitive_dataclass
class PostSelectionOptions(BaseOptions):
    """
    Options for post selecting results.
    """

    enable: bool = False
    r"""Whether to enable Post Selection when performing learning experiments.

    If ``True``, Post Selection is applied to all the learning circuits. In particular, the following
    steps are undertaken:

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
    r"""The type of the X-pulse used for the post selection measurements."""

    strategy: Literal["node", "edge"] = "node"
    r"""The strategy used to decide if a shot should be kept or discarded.

    The available startegies are:

    * ``'node'``: Discard every shot where one or more bits failed to flip. Keep every other shot.
    * ``'edge'``: Discard every shot where there exists a pair of neighbouring qubits for which both of
        the bits failed to flip. Keep every other shot.

    See the dosctrings of :class:`.PostSelector` and :meth:`.PostSelector.compute_mask` for more details.

    Defaults to ``node``.
    """

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitives.
        """
        raise NotImplementedError("Not implemented by `PostSelectionOptions`.")
