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
================================================================
Transpiler passes (:mod:`qiskit_ibm_runtime.transpiler.passes`)
================================================================

.. currentmodule:: qiskit_ibm_runtime.transpiler.passes

A collection of transpiler passes for IBM backends. Refer to
https://docs.quantum.ibm.com/guides/transpile to learn more about
transpilation and passes.

.. autosummary::
   :toctree: ../stubs/

   ConvertIdToDelay

See :mod:`qiskit_ibm_runtime.transpiler.passes.scheduling` for a collection of scheduling passes.
"""

from .basis import ConvertIdToDelay

# circuit scheduling
from .scheduling import ASAPScheduleAnalysis
from .scheduling import PadDynamicalDecoupling
from .scheduling import PadDelay
