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

Primitive options
------------------

.. autosummary::
   :toctree: ../stubs/
   :nosignatures:

   EstimatorOptions
   SamplerOptions


Suboptions
----------

.. autosummary::
   :toctree: ../stubs/
   :nosignatures:

   BaseOptionsModel
   BitFlipChecksOptions
   CalibratorOptions
   DynamicalDecouplingOptions
   EnvironmentOptions
   ExecutionOptions
   ExecutorOptions
   MeasureNoiseLearningOptions
   NoiseLearnerV3Options
   PecOptions
   PostCircuitBitFlipChecksOptions
   PostSelectionOptions
   PreCircuitBitFlipChecksOptions
   ResilienceOptions
   SamplerEnvironmentOptions
   SamplerExecutionOptions
   SimulatorOptions
   TwirlingOptions
   ZneOptions

"""

from .base import BaseOptionsModel
from .bit_flip_checks import (
    BitFlipChecksOptions,
    PostCircuitBitFlipChecksOptions,
    PreCircuitBitFlipChecksOptions,
)
from .calibrator import CalibratorOptions
from .dynamical_decoupling import DynamicalDecouplingOptions
from .environment import EnvironmentOptions, SamplerEnvironmentOptions
from .estimator import EstimatorOptions
from .execution import ExecutionOptions, SamplerExecutionOptions
from .executor import ExecutorOptions
from .measure_noise_learning import MeasureNoiseLearningOptions
from .noise_learner_v3 import NoiseLearnerV3Options
from .pec import PecOptions
from .post_selection import PostSelectionOptions
from .resilience import ResilienceOptions
from .sampler import SamplerOptions
from .simulator import SimulatorOptions
from .twirling import TwirlingOptions
from .zne import ZneOptions
