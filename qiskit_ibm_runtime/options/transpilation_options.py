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

from typing import Optional, List, Union, Literal, get_args
from dataclasses import dataclass

from .utils import _flexible

TranspilationSupportedOptions = Literal[
    "skip_transpilation",
    "initial_layout",
    "layout_method",
    "routing_method",
    "approximation_degree",
]
LayoutMethodType = Literal[
    "trivial",
    "dense",
    "noise_adaptive",
    "sabre",
]
RoutingMethodType = Literal[
    "basic",
    "lookahead",
    "stochastic",
    "sabre",
    "none",
]


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

        approximation_degree: heuristic dial used for circuit approximation
            (1.0=no approximation, 0.0=maximal approximation)
    """

    skip_transpilation: bool = False
    initial_layout: Optional[Union[dict, List]] = None  # TODO: Support Layout
    layout_method: Optional[str] = None
    routing_method: Optional[str] = None
    approximation_degree: Optional[float] = None

    @staticmethod
    def validate_transpilation_options(transpilation_options: dict) -> None:
        """Validate that transpilation options are legal.
        Raises:
            ValueError: if any transpilation option is not supported
            ValueError: if layout_method is not in LayoutMethodType or None.
            ValueError: if routing_method is not in RoutingMethodType or None.
            ValueError: if approximation_degree in not None or in the range 0.0 to 1.0.
        """
        for opt in transpilation_options:
            if not opt in get_args(TranspilationSupportedOptions):
                raise ValueError(f"Unsupported value '{opt}' for transpilation.")
        layout_method = transpilation_options.get("layout_method")
        if not (layout_method in get_args(LayoutMethodType) or layout_method is None):
            raise ValueError(
                f"Unsupported value {layout_method} for layout_method. "
                f"Supported values are {get_args(LayoutMethodType)} and None"
            )
        routing_method = transpilation_options.get("routing_method")
        if not (routing_method in get_args(RoutingMethodType) or routing_method is None):
            raise ValueError(
                f"Unsupported value {routing_method} for routing_method. "
                f"Supported values are {get_args(RoutingMethodType)} and None"
            )
        approximation_degree = transpilation_options.get("approximation_degree")
        if not (approximation_degree is None or 0.0 <= approximation_degree <= 1.0):
            raise ValueError(
                "approximation_degree must be between 0.0 (maximal approximation) "
                "and 1.0 (no approximation)"
            )
