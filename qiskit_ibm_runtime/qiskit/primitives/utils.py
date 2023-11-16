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
"""
Utility functions for primitives
"""
from __future__ import annotations

import sys

from qiskit.circuit import ParameterExpression
from qiskit.quantum_info import SparsePauliOp
from qiskit.quantum_info.operators.base_operator import BaseOperator
from qiskit.quantum_info.operators.symplectic.base_pauli import BasePauli


def init_observable(observable: BaseOperator | str) -> SparsePauliOp:
    """Initialize observable by converting the input to a :class:`~qiskit.quantum_info.SparsePauliOp`.

    Args:
        observable: The observable.

    Returns:
        The observable as :class:`~qiskit.quantum_info.SparsePauliOp`.

    Raises:
        TypeError: If the observable is a :class:`~qiskit.opflow.PauliSumOp` and has a parameterized
            coefficient.
    """
    # This dance is to avoid importing the deprecated `qiskit.opflow` if the user hasn't already
    # done so.  They can't hold a `qiskit.opflow.PauliSumOp` if `qiskit.opflow` hasn't been
    # imported, and we don't want unrelated Qiskit library code to be responsible for the first
    # import, so the deprecation warnings will show.
    if "qiskit.opflow" in sys.modules:
        pauli_sum_check = sys.modules["qiskit.opflow"].PauliSumOp
    else:
        pauli_sum_check = ()

    if isinstance(observable, SparsePauliOp):
        return observable
    elif isinstance(observable, pauli_sum_check):
        if isinstance(observable.coeff, ParameterExpression):
            raise TypeError(
                f"Observable must have numerical coefficient, not {type(observable.coeff)}."
            )
        return observable.coeff * observable.primitive
    elif isinstance(observable, BaseOperator) and not isinstance(observable, BasePauli):
        return SparsePauliOp.from_operator(observable)
    else:
        return SparsePauliOp(observable)
