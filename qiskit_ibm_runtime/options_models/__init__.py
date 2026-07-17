# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
===================================================================
Primitive options models (:mod:`qiskit_ibm_runtime.options_models`)
===================================================================

.. currentmodule:: qiskit_ibm_runtime.options_models

Options that can be passed to the :class:`~qiskit_ibm_runtime.Executor` and
:class:`~qiskit_ibm_runtime.NoiseLearnerV3`.

Classes
=======

Base primitive options
----------------------

.. autosummary::
   :toctree: ../stubs/
   :nosignatures:

   ExecutorOptions
   NoiseLearnerV3Options


Suboptions
----------

.. autosummary::
   :toctree: ../stubs/
   :nosignatures:

   EnvironmentOptions
   ExecutionOptions
   PostSelectionOptions

"""

from .environment import EnvironmentOptions
from .execution import ExecutionOptions
from .executor import ExecutorOptions
from .noise_learner_v3 import NoiseLearnerV3Options
from .post_selection import PostSelectionOptions
from .sampler import SamplerOptions
