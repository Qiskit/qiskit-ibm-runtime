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

"""Exceptions related to the IBM Quantum provider."""

from qiskit.exceptions import QiskitError


class IBMError(QiskitError):
    """Base class for errors raised by the provider modules."""

    pass


class IBMProviderError(IBMError):
    """Base class for errors raise by IBMRuntimeService."""

    pass


class IBMProviderValueError(IBMProviderError):
    """Value errors raised by IBMRuntimeService."""

    pass


class IBMProviderCredentialsNotFound(IBMProviderError):
    """Errors raised when credentials are not found."""

    pass


class IBMProviderMultipleCredentialsFound(IBMProviderError):
    """Errors raised when multiple credentials are found."""

    pass


class IBMProviderCredentialsInvalidFormat(IBMProviderError):
    """Errors raised when the credentials format is invalid."""

    pass


class IBMProviderCredentialsInvalidToken(IBMProviderError):
    """Errors raised when an IBM Quantum token is invalid."""

    pass


class IBMProviderCredentialsInvalidUrl(IBMProviderError):
    """Errors raised when an IBM Quantum URL is invalid."""

    pass


class IBMBackendError(IBMError):
    """Base class for errors raised by the backend modules."""

    pass


class IBMBackendApiError(IBMBackendError):
    """Errors that occur unexpectedly when querying the server."""

    pass


class IBMBackendApiProtocolError(IBMBackendApiError):
    """Errors raised when an unexpected value is received from the server."""

    pass


class IBMBackendValueError(IBMBackendError, ValueError):
    """Value errors raised by the backend modules."""

    pass


class IBMInputValueError(IBMError):
    """Error raised due to invalid input value."""

    pass


class IBMNotAuthorizedError(IBMError):
    """Error raised when a service is invoked from an unauthorized account."""

    pass


class IBMApiError(IBMError):
    """Error raised when a server error encountered."""

    pass


class IBMRuntimeError(IBMError):
    """Base class for errors raised by the runtime service modules."""

    pass


class RuntimeDuplicateProgramError(IBMRuntimeError):
    """Error raised when a program being uploaded already exists."""

    pass


class RuntimeProgramNotFound(IBMRuntimeError):
    """Error raised when a program is not found."""

    pass


class RuntimeJobFailureError(IBMRuntimeError):
    """Error raised when a runtime job failed."""

    pass


class RuntimeJobNotFound(IBMRuntimeError):
    """Error raised when a job is not found."""

    pass


class RuntimeInvalidStateError(IBMRuntimeError):
    """Errors raised when the state is not valid for the operation."""

    pass


class CannotMapCrnToApiHostError(IBMError):
    """Error raised when mapping from CRN to API host fails."""

    pass
