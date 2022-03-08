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

"""Base primitive"""

from abc import ABC, abstractmethod
from typing import Optional, Union, Any

from .ibm_backend import IBMBackend
from .ibm_runtime_service import IBMRuntimeService


class BasePrimitive(ABC):
    """Base primitive"""

    def __init__(
        self,
        service: Optional[IBMRuntimeService],
        backend: Optional[Union[IBMBackend, str]] = None,
    ):
        """Initializes Base Primitive.

        Args:
            service: Optional instance of :class:`qiskit_ibm_runtime.IBMRuntimeService` class,
                defaults to `IBMRuntimeService()` which tries to initialize your default saved account.
            backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                string name of backend, if not specified a backend will be selected automatically
                (IBM Cloud only).
        """
        if not service:
            # try to initialize service with default saved account
            service = IBMRuntimeService()
        self._service = service
        if backend and not isinstance(backend, str):
            backend = backend.name
        self._backend_name = backend

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        pass
