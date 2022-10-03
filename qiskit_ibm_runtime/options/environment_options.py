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

"""Options related to the execution environment."""

from typing import Optional
from dataclasses import dataclass

from .utils import _flexible


@_flexible
@dataclass
class EnvironmentOptions:
    """Options related to the execution environment.

    Args:
        log_level: logging level to set in the execution environment. The valid
            log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
            The default level is ``WARNING``.

        image: The runtime image used to execute the program, specified in
            the form of ``image_name:tag``. Not all accounts are
            authorized to select a different image.

        instance: The hub/group/project to use, in that format. This is only supported
            for ``ibm_quantum`` channel. If ``None``, a hub/group/project that provides
            access to the target backend is randomly selected.
    """

    log_level: str = "WARNING"
    image: Optional[str] = None
    instance: Optional[str] = None
