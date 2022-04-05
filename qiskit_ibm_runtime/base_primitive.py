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
from .qiskit_runtime_service import QiskitRuntimeService


class BasePrimitive(ABC):
    """Base primitive"""

    def __init__(
        self,
        service: Optional[QiskitRuntimeService] = None,
        backend: Optional[Union[IBMBackend, str]] = None,
    ):
        """Initializes Base Primitive.

        Args:
            service: Optional instance of :class:`qiskit_ibm_runtime.QiskitRuntimeService` class,
                defaults to `QiskitRuntimeService()` which tries to initialize your default
                saved account.
            backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                string name of backend, if not specified a backend will be selected automatically
                (IBM Cloud only).
        """
        self._service = service
        self._backend = backend

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        pass
