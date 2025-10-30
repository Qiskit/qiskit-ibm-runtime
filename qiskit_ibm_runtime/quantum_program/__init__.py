# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
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
    QuantumProgramResult
"""

from .quantum_program import QuantumProgram, QuantumProgramItem
from .quantum_program_result import QuantumProgramResult
