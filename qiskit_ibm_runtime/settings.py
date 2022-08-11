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

"""Primitive settings."""

from typing import Optional, List, Dict, Union
from dataclasses import dataclass, asdict

from .runtime_options import RuntimeOptions


@dataclass
class Transpilation:
    """Transpilation settings.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation times.

            * 0: no optimization
            * 1: light optimization
            * 2: heavy optimization
            * 3: even heavier optimization

        skip_transpilation: Whether to skip transpilation.

        initial_layout: Initial position of virtual qubits on physical qubits.
            See :function:`qiskit.compiler.transpile` for more information.

        layout_method: Name of layout selection pass ('trivial', 'dense', 'noise_adaptive', 'sabre')

        routing_method: Name of routing pass ('basic', 'lookahead', 'stochastic', 'sabre', 'none')

        translation_method: Name of translation pass ('unroller', 'translator', 'synthesis')

        approximation_degree (float): heuristic dial used for circuit approximation
            (1.0=no approximation, 0.0=maximal approximation)

        timing_constraints: An optional control hardware restriction on instruction time resolution.
            A quantum computer backend may report a set of restrictions, namely:

            - granularity: An integer value representing minimum pulse gate
              resolution in units of ``dt``. A user-defined pulse gate should have
              duration of a multiple of this granularity value.
            - min_length: An integer value representing minimum pulse gate
              length in units of ``dt``. A user-defined pulse gate should be longer
              than this length.
            - pulse_alignment: An integer value representing a time resolution of gate
              instruction starting time. Gate instruction should start at time which
              is a multiple of the alignment value.
            - acquire_alignment: An integer value representing a time resolution of measure
              instruction starting time. Measure instruction should start at time which
              is a multiple of the alignment value.

            This information will be provided by the backend configuration.
            If the backend doesn't have any restriction on the instruction time allocation,
            then ``timing_constraints`` is None and no adjustment will be performed.

        seed_transpiler: Sets random seed for the stochastic parts of the transpiler
    """

    # TODO: Double check transpilation settings.

    optimization_level: int = 1
    skip_transpilation: bool = False
    initial_layout: Optional[Union[Dict, List]] = None  # TODO: Support Layout
    layout_method: Optional[str] = None
    routing_method: Optional[str] = None
    translation_method: Optional[str] = None
    approximation_degree: Optional[float] = None
    timing_constraints: Optional[Dict[str, int]] = None
    seed_transpiler: Optional[int] = None

@dataclass
class Resilience:
    """Resilience settings.

    Args:
        level: How much resilience to build against errors.
            Higher levels generate more accurate results,
            at the expense of longer processing times.
            * 0: no resilience
            * 1: light resilience
    """

    level: int = 0


@dataclass
class Settings:

    transpilation: Transpilation = Transpilation()
    resilience: Resilience = Resilience()
    service_options: RuntimeOptions = RuntimeOptions()

    def _to_program_inputs(self) -> Dict:
        # TODO: Remove this once primitive program is updated to use optimization_level.
        transpilation_settings = asdict(self.transpilation)
        transpilation_settings["optimization_settings"] = {
            "level": transpilation_settings["optimization_level"]
        }
        return {
            "resilience_settings": asdict(self.resilience),
            "transpilation_settings": transpilation_settings,
        }
