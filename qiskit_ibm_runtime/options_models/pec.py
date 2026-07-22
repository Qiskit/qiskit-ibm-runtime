# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Probabalistic error cancellation mitigation options."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .base import BaseOptionsModel


class PecOptions(BaseOptionsModel):
    """Probabalistic error cancellation mitigation options. This is only used by V2 Estimator."""

    max_overhead: Annotated[float, Field(ge=0)] | None = 100
    """The maximum circuit sampling overhead allowed, or ``None`` for no maximum.

    In order to remove the full learned noise, the number of randomizations should be multiplied by
    the sampling overhead, which is ``gamma^2``.

    The maximum overhead limits the sampling overhead allowed.
    """

    noise_gain: Annotated[float, Field(ge=0)] | Literal["auto"] = "auto"
    """The amount by which to scale the noise.

    The amount by which to scale the noise, where:

    * A value of ``0`` corresponds to removing the full learned noise.
    * A value of ``1`` corresponds to no removal of the learned noise.
    * A value between ``0`` and ``1`` corresponds to partially removing the learned noise.
    * A value greater than one corresponds to amplifying the learned noise.

    If ``"auto"``, the value in the range ``[0, 1]`` will be chosen automatically for each input
    PUB by the formula ``1 - log(max_overhead) / log(gamma^2)``.
    """
