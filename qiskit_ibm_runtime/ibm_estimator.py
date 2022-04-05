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

"""Qiskit Runtime Estimator primitive service."""

import warnings

from typing import Any, Iterable, Optional, Union

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import SparsePauliOp

from .base_primitive import BasePrimitive
from .estimator import Estimator


class IBMEstimator(BasePrimitive):
    """Deprecated, use :class:`~qiskit_ibm_runtime.Estimator` instead."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initalizes IBMEstimator."""
        super().__init__(*args, **kwargs)
        warnings.warn(
            "IBMEstimator class is deprecated and will "
            "be removed in a future release. "
            "You can now use qiskit_ibm_runtime.Estimator class instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def __call__(  # type: ignore[override]
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        observables: Iterable[SparsePauliOp],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        skip_transpilation: bool = False,
    ) -> Estimator:
        """Initializes the Estimator primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            observables: a list of :class:`~qiskit.quantum_info.SparsePauliOp`
            parameters: a list of parameters of the quantum circuits.
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`) specifying the order
                in which parameter values will be bound.
            skip_transpilation: Transpilation is skipped if set to True.
                False by default.

        Returns:
            An instance of :class:`qiskit_ibm_runtime.estimator.Estimator`.
        """
        # pylint: disable=arguments-differ
        options = None
        if self._backend:
            options = {"backend": self._backend}
        return Estimator(
            circuits=circuits,
            observables=observables,
            parameters=parameters,
            skip_transpilation=skip_transpilation,
            service=self._service,
            options=options,
        )
