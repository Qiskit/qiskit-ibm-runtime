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

"""
==========================================================
Execution Spans (:mod:`qiskit_ibm_runtime.execution_span`)
==========================================================

.. currentmodule:: qiskit_ibm_runtime.execution_span

Overview
========

An :class:`~.ExecutionSpans` class instance is an iterable of :class:`~.ExecutionSpan`\\s, where 
each iterand gives timing information about a chunk of data. Execution spans are returned as part 
of the metadata of a primitive job result.

Classes
=======

.. autosummary::
    :toctree: ../stubs/

    ExecutionSpan
    ExecutionSpans
    ShapeType
    SliceSpan
"""

from .execution_span import ExecutionSpan, ShapeType
from .execution_spans import ExecutionSpans
from .slice_span import SliceSpan
