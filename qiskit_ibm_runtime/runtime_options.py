# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Runtime options that control the execution environment."""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Union

from .exceptions import IBMInputValueError
from .ibm_backend import IBMBackend
from .utils.deprecation import deprecate_arguments


@dataclass
class RuntimeOptions:
    """Class for representing runtime execution options.

    Args:
        backend: target backend to run on. This is required for ``ibm_quantum`` runtime.
        image: the runtime image used to execute the program, specified in
            the form of ``image_name:tag``. Not all accounts are
            authorized to select a different image.
        log_level: logging level to set in the execution environment. The valid
            log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
            The default level is ``WARNING``.
    """

    def __init__(
        self,
        backend_name: Optional[str] = None,
        backend: Optional[str] = None,
        image: Optional[str] = None,
        log_level: Optional[str] = None,
    ) -> None:
        # TODO: We can go back to a proper dataclass once backend_name is removed.
        if backend_name:
            deprecate_arguments(
                deprecated="backend_name",
                version="0.7",
                remedy='Please use "backend" instead.',
            )

        self.backend = backend or backend_name
        if self.backend is not None:
            if isinstance(self.backend, IBMBackend):
                self.backend = self.backend.name
            elif not isinstance(self.backend, str):
                raise IBMInputValueError(
                    f"Invalid backend type {type(self.backend)} specified. "
                    "It should be either the string name of the "
                    "backend or an instance of 'IBMBackend' class"
                )
        self.image = image
        self.log_level = log_level

    def validate(self, channel: str) -> None:
        """Validate options.

        Args:
            channel: channel type.

        Raises:
            IBMInputValueError: If one or more option is invalid.
        """
        if self.image and not re.match(
            "[a-zA-Z0-9]+([/.\\-_][a-zA-Z0-9]+)*:[a-zA-Z0-9]+([.\\-_][a-zA-Z0-9]+)*$",
            self.image,
        ):
            raise IBMInputValueError('"image" needs to be in form of image_name:tag')

        if channel == "ibm_quantum" and not self.backend:
            raise IBMInputValueError(
                '"backend" is required field in "options" for ``ibm_quantum`` runtime.'
            )

        if self.log_level and not isinstance(
            logging.getLevelName(self.log_level.upper()), int
        ):
            raise IBMInputValueError(
                f"{self.log_level} is not a valid log level. The valid log levels are: `DEBUG`, "
                f"`INFO`, `WARNING`, `ERROR`, and `CRITICAL`."
            )

    @property
    def backend_name(self) -> str:
        """Return the backend option.

        Returns:
            Name of the backend to use.
        """
        return self.backend

    @backend_name.setter
    def backend_name(self, backend: Optional[Union[str, IBMBackend]]) -> None:
        """Set the backend to use.

        Args:
            backend: Backend to use.
        """
        deprecate_arguments(
            deprecated="backend_name",
            version="0.7",
            remedy="Please use backend instead.",
        )
        self.backend = backend

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(backend={self.backend}, image={self.image}, log_level={self.log_level})"
        )
