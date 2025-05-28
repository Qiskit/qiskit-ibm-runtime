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

from typing import Optional, Callable, List, Literal

from .utils import primitive_dataclass

LogLevelType = Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]


@primitive_dataclass
class EnvironmentOptions:
    """Options related to the execution environment."""

    log_level: LogLevelType = "WARNING"
    r"""logging level to set in the execution environment. The valid
        log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.

        Default: ``WARNING``.
    """
    callback: Optional[Callable] = None
    r"""(DEPRECATED) Callback function to be invoked for any interim results and final result.
        The callback function will receive 2 positional parameters:

            1. Job ID
            2. Job result.

        Default: ``None``.
    """
    job_tags: Optional[List] = None
    r"""Tags to be assigned to the job. The tags can subsequently be used
        as a filter in the :meth:`qiskit_ibm_runtime.qiskit_runtime_service.jobs()`
        function call. 
        
        Default: ``None``.
    """
    private: Optional[bool] = False
    r"""Boolean that indicates whether the job is marked as private. When set to true, 
        input parameters are not returned, and the results can only be read once. 
        After the job is completed, input parameters are deleted from the service. 
        After the results are read, these are also deleted from the service. 
        When set to false, the input parameters and results follow the 
        standard retention behavior of the API.

        Default: False.
    """
