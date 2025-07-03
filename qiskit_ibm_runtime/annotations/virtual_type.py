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

"""Virtual type."""

from enum import StrEnum
from typing import Literal, TypeAlias


class VirtualType(StrEnum):
    """Name identifiers for virtual gate types."""

    PAULI = "pauli"
    """The projective Pauli group."""

    C1 = "c1"
    """The single-qubit Clifford group."""

    U2 = "u2"
    r"""The :math:`2 \times 2` unitary group."""

    Z2 = "z2"
    """The two-element cyclic group."""


TWIRLING_GROUPS = frozenset([VirtualType.PAULI])
"""Those :class:`VirtualType`\\s that represent unitary groups and have twirling support."""


GroupLiteral: TypeAlias = VirtualType | Literal["pauli"]
"""The type of group by which to twirl.

 * ``pauli``: The projective Pauli group.
"""