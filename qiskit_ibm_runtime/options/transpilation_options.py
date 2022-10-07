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

"""Transpilation options."""

from typing import Optional, List, Union, Dict
from dataclasses import dataclass

from .utils import _flexible


@_flexible
@dataclass
class TranspilationOptions:
    """Transpilation options.

    Args:

        skip_transpilation: Whether to skip transpilation.

        initial_layout: Initial position of virtual qubits on physical qubits.
            See ``qiskit.compiler.transpile`` for more information.

        layout_method: Name of layout selection pass. One of
            'trivial', 'dense', 'noise_adaptive', 'sabre'.

        routing_method: Name of routing pass.
            One of 'basic', 'lookahead', 'stochastic', 'sabre', 'none'.

        translation_method: Name of translation pass. One of 'unroller', 'translator', 'synthesis'.

        approximation_degree: heuristic dial used for circuit approximation
            (1.0=no approximation, 0.0=maximal approximation)

        timing_constraints: An optional control hardware restriction on instruction time
            resolution. A quantum computer backend may report a set of restrictions, namely:

            * granularity: An integer value representing minimum pulse gate
                resolution in units of ``dt``. A user-defined pulse gate should have
                duration of a multiple of this granularity value.

            * min_length: An integer value representing minimum pulse gate
                length in units of ``dt``. A user-defined pulse gate should be longer
                than this length.

            * pulse_alignment: An integer value representing a time resolution of gate
                instruction starting time. Gate instruction should start at time which
                is a multiple of the alignment value.

            * acquire_alignment: An integer value representing a time resolution of measure
                instruction starting time. Measure instruction should start at time which
                is a multiple of the alignment value.

                This information will be provided by the backend configuration.
                If the backend doesn't have any restriction on the instruction time allocation,
                then ``timing_constraints`` is None and no adjustment will be performed.
    """

    # TODO: Double check transpilation settings.

    skip_transpilation: bool = False
    initial_layout: Optional[Union[dict, List]] = None  # TODO: Support Layout
    layout_method: Optional[str] = None
    routing_method: Optional[str] = None
    translation_method: Optional[str] = None
    approximation_degree: Optional[float] = None
    timing_constraints: Optional[Dict[str, int]] = None
