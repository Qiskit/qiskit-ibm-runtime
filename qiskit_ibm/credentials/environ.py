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

"""Utilities for reading credentials from environment variables."""

import os
from typing import Dict

from .credentials import Credentials
from .hubgroupproject import HubGroupProject

VARIABLES_MAP = {
    'QISKIT_IBM_API_TOKEN': 'token',
    'QISKIT_IBM_API_URL': 'url',
    'QISKIT_IBM_HUB': 'hub',
    'QISKIT_IBM_GROUP': 'group',
    'QISKIT_IBM_PROJECT': 'project'
}
"""Dictionary that maps `ENV_VARIABLE_NAME` to credential parameter."""


def read_credentials_from_environ() -> Dict[HubGroupProject, Credentials]:
    """Extract credentials from the environment variables.

    Returns:
        A dictionary containing the credentials, in the
        ``{credentials_unique_id: Credentials}`` format.
    """
    # The token is the only required parameter.
    if not (os.getenv('QISKIT_IBM_API_TOKEN') and os.getenv('QISKIT_IBM_API_URL')):
        return {}

    # Build the credentials based on environment variables.
    credentials_dict = {}
    hub = None
    group = None
    project = None

    for envar_name, credential_key in VARIABLES_MAP.items():
        if os.getenv(envar_name):
            credentials_dict[credential_key] = os.getenv(envar_name)
            if envar_name == 'QISKIT_IBM_API_URL':
                credentials_dict['auth_url'] = os.getenv(envar_name)
            elif envar_name == 'QISKIT_IBM_HUB':
                hub = os.getenv(envar_name)
            elif envar_name == 'QISKIT_IBM_GROUP':
                group = os.getenv(envar_name)
            elif envar_name == 'QISKIT_IBM_PROJECT':
                project = os.getenv(envar_name)

    if all([hub, group, project]):
        credentials_dict['default_provider'] = HubGroupProject(hub, group, project)

    credentials = Credentials(**credentials_dict)  # type: ignore[arg-type]
    return {credentials.unique_id(): credentials}
