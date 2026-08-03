# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utilities related to conversion."""

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser, tz

from ..exceptions import IBMInputValueError


def utc_to_local(utc_dt: datetime | str) -> datetime:
    """Convert a UTC ``datetime`` object or string to a local timezone ``datetime``.

    Args:
        utc_dt: Input UTC `datetime` or string.

    Returns:
        A ``datetime`` with the local timezone.

    Raises:
        TypeError: If the input parameter value is not valid.
    """
    if isinstance(utc_dt, str):
        utc_dt = parser.parse(utc_dt)
    if not isinstance(utc_dt, datetime):
        raise TypeError("Input `utc_dt` is not string or datetime.")
    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    local_dt = utc_dt.astimezone(tz.tzlocal())
    return local_dt


def local_to_utc(local_dt: datetime | str) -> datetime:
    """Convert a local ``datetime`` object or string to a UTC ``datetime``.

    Args:
        local_dt: Input local ``datetime`` or string.

    Returns:
        A ``datetime`` in UTC.

    Raises:
        TypeError: If the input parameter value is not valid.
    """
    if isinstance(local_dt, str):
        local_dt = parser.parse(local_dt)
    if not isinstance(local_dt, datetime):
        raise TypeError("Input `local_dt` is not string or datetime.")

    # Input is considered local if it's ``utcoffset()`` is ``None`` or none-zero.
    if local_dt.utcoffset() is None or local_dt.utcoffset() != timedelta(0):
        local_dt = local_dt.replace(tzinfo=tz.tzlocal())
        return local_dt.astimezone(tz.UTC)
    return local_dt  # Already in UTC.


def utc_to_local_all(data: Any) -> Any:
    """Recursively convert all ``datetime`` in the input data from local time to UTC.

    Note:
        Only lists and dictionaries are traversed.

    Args:
        data: Data to be converted.

    Returns:
        Converted data.
    """
    if isinstance(data, datetime):
        return utc_to_local(data)
    elif isinstance(data, list):
        return [utc_to_local_all(elem) for elem in data]
    elif isinstance(data, dict):
        return {key: utc_to_local_all(elem) for key, elem in data.items()}
    return data


def hms_to_seconds(hms: str, msg_prefix: str = "") -> int:
    """Convert duration specified as hours minutes seconds to seconds.

    Args:
        hms: The string input duration (in hours minutes seconds). Ex: 2h 10m 20s
        msg_prefix: Additional message to prefix the error.

    Returns:
        Total seconds (int) in the duration.

    Raises:
        IBMInputValueError: when the given hms string is in an invalid format
    """
    parsed_time = re.findall(r"(\d+[dhms])", hms)
    total_seconds = 0

    if parsed_time:
        for time_unit in parsed_time:
            unit = time_unit[-1]
            value = int(time_unit[:-1])
            if unit == "d":
                total_seconds += value * 86400
            elif unit == "h":
                total_seconds += value * 3600
            elif unit == "m":
                total_seconds += value * 60
            elif unit == "s":
                total_seconds += value
            else:
                raise IBMInputValueError(f"{msg_prefix} Invalid input: {unit}")
    else:
        raise IBMInputValueError(f"{msg_prefix} Invalid input: {parsed_time}")

    return total_seconds
