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
from typing import Optional, List

from qiskit.utils.deprecation import deprecate_arguments

from .exceptions import IBMInputValueError
from .options import Options
from .utils.deprecation import issue_deprecation_msg


@dataclass
class RuntimeOptions:
    """Class for representing generic runtime execution options."""

    @deprecate_arguments({"backend_name": "backend"})
    def __init__(
        self,
        backend: Optional[str] = None,
        image: Optional[str] = None,
        log_level: Optional[str] = None,
        job_tags: Optional[List[str]] = None,
        max_execution_time: Optional[int] = None
    ) -> None:
        """RuntimeOptions constructor.

        Args:
            backend: target backend to run on. This is required for ``ibm_quantum`` channel.
            image: the runtime image used to execute the program, specified in
                the form of ``image_name:tag``. Not all accounts are
                authorized to select a different image.
            log_level: logging level to set in the execution environment. The valid
                log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
                The default level is ``WARNING``.
            job_tags: Tags to be assigned to the job. The tags can subsequently be used
                as a filter in the :meth:`jobs()` function call.
            max_execution_time: Maximum execution time in seconds. This overrides
                the max_execution_time of the program and cannot exceed it.
        """
        self.backend = backend
        self.image = image
        self.log_level = log_level
        self.job_tags = job_tags
        self.max_execution_time = max_execution_time

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

    def _to_new_options(self) -> Options:
        return Options(
            log_level=self.log_level,
            experimental={"image": self.image},
        )

    @property
    def backend_name(self) -> str:
        """Return backend.

        Returns:
            Backend name.
        """
        return self.backend

    @backend_name.setter
    def backend_name(self, name: str) -> None:
        """Set backend name.

        Args:
            name: Backend to use.
        """
        issue_deprecation_msg(
            msg="The 'backend_name' attribute is deprecated",
            version="0.7",
            remedy="Please use 'backend' instead.",
        )
        self._backend = name
