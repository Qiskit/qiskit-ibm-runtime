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

"""Simulator options."""

from typing import Optional, List, Union, TYPE_CHECKING
from dataclasses import dataclass

from .utils import _flexible

if TYPE_CHECKING:
    import qiskit_aer


@_flexible
@dataclass()
class SimulatorOptions:
    """Simulator options.

    For best practice in simulating a backend make sure to pass the
    basis gates and coupling map of that backend.

    Args:
        noise_model: Noise model for the simulator.

        seed_simulator: Random seed to control sampling.

        coupling_map: Directed coupling map to target in mapping. If
            the coupling map is symmetric, both directions need to be specified.
            Each entry in the list specifies a directed two-qubit interactions,
            e.g: ``[[0, 1], [0, 3], [1, 2], [1, 5], [2, 5], [4, 1], [5, 3]]``

        basis_gates: List of basis gate names to unroll to. For example,
            ``['u1', 'u2', 'u3', 'cx']``. If ``None``, do not unroll.
    """

    noise_model: Optional[Union[dict, "qiskit_aer.noise.noise_model.NoiseModel"]] = None
    seed_simulator: Optional[int] = None
    coupling_map: Optional[List[List[int]]] = None
    basis_gates: Optional[List[str]] = None
