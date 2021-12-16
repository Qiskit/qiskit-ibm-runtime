# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utility functions related to storing account configuration on disk."""

import json
import os
from typing import Optional, Union


def save_config(
    filename: str,
    name: str,
    config: dict,
) -> None:
    """Save configuration data in a JSON file under the given name."""

    _ensure_file_exists(filename)

    with open(filename, mode="r") as json_in:
        data = json.load(json_in)

    with open(filename, mode="w") as json_out:
        data[name] = config
        json.dump(data, json_out, sort_keys=True, indent=4)


def read_config(
    filename: str,
    name: Optional[str] = None,
) -> Union[dict, None]:
    """Save configuration data from a JSON file."""

    _ensure_file_exists(filename)

    with open(filename) as json_file:
        data = json.load(json_file)
        if name is None:
            return data
        if name in data:
            return data[name]

        return None


def delete_config(
    filename: str,
    name: str,
) -> bool:
    """Delete configuration data from a JSON file."""

    _ensure_file_exists(filename)
    with open(filename, mode="r") as json_in:
        data = json.load(json_in)

    if name in data:
        with open(filename, mode="w") as json_out:
            del data[name]
            json.dump(data, json_out, sort_keys=True, indent=4)
            return True

    return False


def _ensure_file_exists(filename: str, initial_content: str = "{}") -> None:
    if not os.path.isfile(filename):

        # create parent directories
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # initialize file
        with open(filename, mode="w") as json_file:
            json_file.write(initial_content)
