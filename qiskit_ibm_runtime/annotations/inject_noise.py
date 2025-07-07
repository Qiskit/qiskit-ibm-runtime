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

"""Inject noise annotation."""

from typing import Any

from qiskit.circuit import Annotation


class InjectNoise(Annotation):
    """Directive to inject noise into a ``box`` instruction.

    Args:
        ref: A unique identifier of the map from which to inject noise.
    """

    namespace = "runtime.inject_noise"

    def __init__(self, ref: str):
        self.ref = ref

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, InjectNoise) and self.ref == other.ref
