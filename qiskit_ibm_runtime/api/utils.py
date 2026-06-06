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

"""Common functionality for interacting with the API."""

from __future__ import annotations

import copy
import re
from typing import Any
from urllib.parse import urlparse

from ..utils.utils import is_crn


def filter_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return the data with certain fields filtered.

    Data to be filtered out includes hub/group/project information.

    Args:
        data: Original data to be filtered.

    Returns:
        Filtered data.
    """
    if not isinstance(data, dict):
        return data  # type: ignore[unreachable]

    data_to_filter = copy.deepcopy(data)
    keys_to_filter = ["hubInfo"]
    _filter_value(data_to_filter, keys_to_filter)  # type: ignore[arg-type]
    return data_to_filter


def _filter_value(data: dict[str, Any], filter_keys: list[str | tuple[str, str]]) -> None:
    """Recursive function to filter out the values of the input keys.

    Args:
        data: Data to be filtered
        filter_keys: A list of keys whose values are to be filtered out. Each
            item in the list can be a string or a tuple. A tuple indicates nested
            keys, such as ``{'backend': {'name': ...}}`` and must have a length
            of 2.
    """
    for key, value in data.items():
        for filter_key in filter_keys:
            if isinstance(filter_key, str) and key == filter_key:
                data[key] = "..."
            elif key == filter_key[0] and filter_key[1] in value:
                data[filter_key[0]][filter_key[1]] = "..."
            elif isinstance(value, dict):
                _filter_value(value, filter_keys)


def default_runtime_url_resolver(
    url: str,
    instance: str,
    private_endpoint: bool = False,
    channel: str = "ibm_quantum_platform",
) -> str:
    """Computes the Runtime API base URL based on the provided input parameters.

    Args:
        url: The raw URL to access the service, for example, "https://cloud.ibm.com".
        instance: The instance CRN.
        private_endpoint: Connect to private API URL.
        channel: This input parameter is currently UNUSED and kept for
            backwards compatibility purposes only.

    Returns:
        Runtime API base URL
    """
    # URL won't be modified if it contains "experimental"
    api_host = url

    # In all other cases, compute runtime API URL based on CRN and raw URL
    if is_crn(instance) and not _is_experimental_runtime_url(url):
        parsed_url = urlparse(url)
        if private_endpoint:
            api_host = (
                f"{parsed_url.scheme}://private.{_location_from_crn(instance)}"
                f".quantum.{parsed_url.hostname}/api/v1"
            )
        else:
            # ibm_quantum_platform and ibm_cloud share the URL. If the raw URL is
            # "https://cloud.ibm.com" (default), then the output api_host will be:
            #  - for us-east: "https://quantum.cloud.ibm.com/api/v1"
            #  - for other regions, ie. eu-de: "https://eu-de.quantum.cloud.ibm.com/api/v1"
            region = _location_from_crn(instance)
            region_prefix = "" if region == "us-east" else f"{region}."
            api_host = f"{parsed_url.scheme}://{region_prefix}quantum.{parsed_url.hostname}/api/v1"

    return api_host


def _is_experimental_runtime_url(url: str) -> bool:
    """Checks if the provided url points to an experimental runtime cluster.

    This type of URLs is used for internal development purposes only.

    Args:
        url: The URL.
    """
    return isinstance(url, str) and "experimental" in url


def _location_from_crn(crn: str) -> str:
    """Computes the location from a given CRN.

    Args:
        crn: A CRN (format: https://cloud.ibm.com/docs/account?topic=account-crn#format-crn)

    Returns:
        The location.
    """
    pattern = "(.*?):(.*?):(.*?):(.*?):(.*?):(.*?):.*"
    return re.search(pattern, crn).group(6)


def cname_from_crn(crn: str) -> str:
    """Computes the CNAME ('bluemix' or 'staging') from a given CRN.

    Args:
        crn: A CRN (format: https://cloud.ibm.com/docs/account?topic=account-crn#format-crn)

    Returns:
        The location.
    """
    if is_crn(crn):
        pattern = "(.*?):(.*?):(.*?):(.*?):(.*?):(.*?):.*"
        return re.search(pattern, crn).group(3)
    return None
