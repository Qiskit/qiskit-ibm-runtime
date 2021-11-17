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

"""Model for representing a hub/group/project id tuple."""

from typing import Tuple, Optional

from .exceptions import HubGroupProjectIDInvalidStateError


class HubGroupProjectID:
    """Class for representing a hub/group/project id."""

    def __init__(self, hub: str = None, group: str = None, project: str = None) -> None:
        """HubGroupProjectID constructor."""
        self.hub = hub
        self.group = group
        self.project = project

    @classmethod
    def from_stored_format(cls, hgp_id: str) -> "HubGroupProjectID":
        """Instantiates a ``HubGroupProjectID`` instance from a string.

        Note:
            The format for the string is ``<hub_name>/<group_name>/<project_name>``.
            It is saved inside the configuration file to specify a default provider.

        Raises:
            HubGroupProjectIDInvalidStateError: If the specified string, used for conversion, is
                in an invalid format.

        Returns:
            A ``HubGroupProjectID`` instance.
        """
        try:
            hub, group, project = hgp_id.split("/")
            if (not hub) or (not group) or (not project):
                raise HubGroupProjectIDInvalidStateError(
                    'The hub/group/project id "{}" is in an invalid format. '
                    'Every field must be specified: hub = "{}", group = "{}", project = "{}".'.format(
                        hgp_id, hub, group, project
                    )
                )
        except ValueError:
            # Not enough, or too many, values were provided.
            raise HubGroupProjectIDInvalidStateError(
                'The hub/group/project id "{}" is in an invalid format. '
                'Use the "<hub_name>/<group_name>/<project_name>" format.'.format(
                    hgp_id
                )
            )

        return cls(hub, group, project)

    @classmethod
    def from_credentials(
        cls, credentials_obj: "Credentials"  # type: ignore
    ) -> "HubGroupProjectID":
        """Instantiates a ``HubGroupProjectID`` instance from ``Credentials``.

        Returns:
            A ``HubGroupProjectID`` instance.
        """
        hub, group, project = [
            getattr(credentials_obj, key) for key in ["hub", "group", "project"]
        ]
        return cls(hub, group, project)

    def to_stored_format(self) -> str:
        """Returns ``HubGroupProjectID`` as a string.

        Note:
            The format of the string returned is ``<hub_name>/<group_name>/<project_name>``.
            It is used to save a default hub/group/project in the configuration file.

        Raises:
            HubGroupProjectIDInvalidStateError: If the ``HubGroupProjectID`` cannot be
                represented as a string to store on disk (i.e. Some of the hub, group,
                project fields are empty strings or ``None``).

        Returns:
             A string representation of the hub/group/project id, used to store to disk.
        """
        if (not self.hub) or (not self.group) or (not self.project):
            raise HubGroupProjectIDInvalidStateError(
                "The hub/group/project id cannot be represented in the stored format. "
                'Every field must be specified: hub = "{}", group = "{}", project = "{}".'.format(
                    self.hub, self.group, self.project
                )
            )
        return "/".join([self.hub, self.group, self.project])

    def to_tuple(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns ``HubGroupProjectID`` as a tuple."""
        return self.hub, self.group, self.project

    def __eq__(self, other: "HubGroupProjectID") -> bool:  # type: ignore
        """Two instances are equal if they define the same hub, group, project."""
        return (self.hub, self.group, self.project) == (
            other.hub,
            other.group,
            other.project,
        )

    def __hash__(self) -> int:
        """Returns a hash for an instance."""
        return hash((self.hub, self.group, self.project))
