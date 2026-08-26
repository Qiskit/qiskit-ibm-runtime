# This code is part of Qiskit.
#
# (C) Copyright IBM 2025, 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
============================================================
Quantum Programs (:mod:`qiskit_ibm_runtime.quantum_program`)
============================================================

.. currentmodule:: qiskit_ibm_runtime.quantum_program

Overview
========

A quantum program consists of a list of ordered elements, each of which contains a single
circuit and an array of associated parameter values. Executing a quantum program will
sample the outcome of each circuit for the specified number of ``shots`` for each set of
circuit arguments provided.


Classes
=======

.. autosummary::
    :toctree: ../stubs/
    :nosignatures:

    QuantumProgram
    QuantumProgramItem
    CircuitItem
    SamplexItem
"""

from ..utils.deprecation import issue_deprecation_msg
from .quantum_program import QuantumProgram

_DEPRECATED_NAMES = frozenset({"CircuitItem", "QuantumProgramItem", "SamplexItem", "DataTree"})


def __getattr__(name: str) -> object:
    if name in _DEPRECATED_NAMES:
        import samplomatic.quantum_program as _sq

        issue_deprecation_msg(
            msg=f"Importing '{name}' from 'qiskit_ibm_runtime.quantum_program' is deprecated",
            version="0.50.0",
            remedy=f"Import '{name}' from 'samplomatic.quantum_program' instead.",
            stacklevel=2,
        )
        return getattr(_sq, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
