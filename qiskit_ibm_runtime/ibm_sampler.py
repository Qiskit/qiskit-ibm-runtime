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

"""Qiskit Runtime Sampler primitive service."""

import warnings

from typing import Any, Optional, Iterable, Union

from qiskit.circuit import QuantumCircuit, Parameter

from .base_primitive import BasePrimitive
from .sampler import Sampler


class IBMSampler(BasePrimitive):
    """Deprecated, use :class:`~qiskit_ibm_runtime.Sampler` instead."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initalizes IBMSampler."""
        super().__init__(*args, **kwargs)
        warnings.warn(
            "IBMSampler class is deprecated and will "
            "be removed in a future release. "
            "You can now use qiskit_ibm_runtime.Sampler class instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def __call__(  # type: ignore[override]
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        skip_transpilation: bool = False,
    ) -> Sampler:
        """Initializes the Sampler primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameters: A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`).
            skip_transpilation: Transpilation is skipped if set to True.
                False by default.

        Returns:
            An instance of :class:`qiskit_ibm_runtime.sampler.Sampler`.
        """
        # pylint: disable=arguments-differ
        options = None
        if self._backend:
            options = {"backend": self._backend}
        return Sampler(
            circuits=circuits,
            parameters=parameters,
            skip_transpilation=skip_transpilation,
            service=self._service,
            options=options,
        )
