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

"""
======================================================
Credentials (:mod:`qiskit_ibm_runtime.credentials`)
======================================================

.. currentmodule:: qiskit_ibm_runtime.credentials

Utilities for working with IBM Quantum account credentials.

Classes
=========

.. autosummary::
    :toctree: ../stubs/

    Credentials

Exceptions
==========
.. autosummary::
    :toctree: ../stubs/


"""

import logging
from collections import OrderedDict
from typing import Dict, Tuple, Any

from .credentials import Credentials
from .environ import read_credentials_from_environ
from .exceptions import (
    CredentialsError,
    HubGroupProjectIDInvalidStateError,
)
from .hub_group_project_id import HubGroupProjectID

logger = logging.getLogger(__name__)


def discover_credentials() -> Tuple[Dict[HubGroupProjectID, Credentials], Dict]:
    """Automatically discover credentials for IBM Quantum.

    This method looks for credentials in the following places in order and
    returns the first ones found:

        1. The environment variables.

    Raises:
        HubGroupProjectIDInvalidStateError: If the default provider stored on
            disk could not be parsed.

    Returns:
        A tuple containing the found credentials and the stored
        preferences, if any, in the configuration file. The format
        for the found credentials is ``{credentials_unique_id: Credentials}``,
        whereas the preferences is ``{credentials_unique_id: {category: {key: val}}}``.
    """
    credentials_: Dict[HubGroupProjectID, Credentials] = {}
    preferences: Dict[HubGroupProjectID, Dict] = {}

    # dict[str:function] that defines the different locations for looking for
    # credentials, and their precedence order.
    readers = OrderedDict(
        [
            ("environment variables", (read_credentials_from_environ, {})),
        ]
    )  # type: OrderedDict[str, Any]

    # Attempt to read the credentials from the different sources.
    for display_name, (reader_function, kwargs) in readers.items():
        try:
            stored_account_info = reader_function(**kwargs)  # type: ignore[arg-type]
            if display_name == "qiskitrc":
                # Read from `qiskitrc`, which may have stored preferences.
                credentials_, preferences = stored_account_info
            else:
                credentials_ = stored_account_info
            if credentials_:
                logger.info("Using credentials from %s", display_name)
                break
        except CredentialsError as ex:
            logger.warning(
                "Automatic discovery of %s credentials failed: %s",
                display_name,
                str(ex),
            )

    return credentials_, preferences
