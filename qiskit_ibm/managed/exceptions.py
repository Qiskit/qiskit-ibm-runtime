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

"""Exception for the Job Manager modules."""

from ..exceptions import IBMError


class IBMJobManagerError(IBMError):
    """Base class for errors raise by the Job Manager."""
    pass


class IBMJobManagerInvalidStateError(IBMJobManagerError):
    """Errors raised when an operation is invoked in an invalid state."""
    pass


class IBMJobManagerTimeoutError(IBMJobManagerError):
    """Errors raised when a Job Manager operation times out."""
    pass


class IBMJobManagerJobNotFound(IBMJobManagerError):
    """Errors raised when a job cannot be found."""
    pass


class IBMManagedResultDataNotAvailable(IBMJobManagerError):
    """Errors raised when result data is not available."""
    pass


class IBMJobManagerUnknownJobSet(IBMJobManagerError):
    """Errors raised when the job set ID is unknown."""
    pass
