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

"""Calibrator results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime


class CalibratorResult:
    """The results of a calibration job."""

    start: datetime.datetime
    """The start time of the calibration in UTC."""

    stop: datetime.datetime
    """The stop time of the calibration in UTC."""

    def __init__(self, start: datetime.datetime, stop: datetime.datetime):
        self.start = start
        self.stop = stop

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(start='{self.start}', stop='{self.stop}')>"
