# This code is part of Qiskit.
#
# (C) Copyright IBM 2022, 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
=====================================================
Primitive options (:mod:`qiskit_ibm_runtime.options`)
=====================================================

.. currentmodule:: qiskit_ibm_runtime.options

Options that can be passed to the Qiskit Runtime primitives.

V2 Primitives
=============

``SamplerV2`` and ``EstimatorV2`` each have their own options. You can use the
``options`` attribute to set the options. For example::

   from qiskit_ibm_runtime import QiskitRuntimeService, EstimatorV2

   service = QiskitRuntimeService()
   backend = service.least_busy(operational=True, simulator=False)
   estimator = EstimatorV2(backend=backend)
   estimator.options.resilience_level = 1

You can also use the ``update()`` method to do bulk update. For example::

   from qiskit_ibm_runtime import QiskitRuntimeService, EstimatorV2

   service = QiskitRuntimeService()
   backend = service.least_busy(operational=True, simulator=False)
   estimator = EstimatorV2(backend=backend)
   estimator.options.update(resilience_level=1)

Refer to :class:`SamplerOptions` and :class:`EstimatorOptions` for V2 Sampler and
V2 Estimator options, respectively.

.. note::
   If an option is not specified, the server default value is used. The
   default values are subject to change. Refer to this current module's documentation
   for the latest defaults.

Classes
=======

Base primitive options
----------------------

.. autosummary::
   :toctree: ../stubs/

   EstimatorOptions
   SamplerOptions


Suboptions
----------

.. autosummary::
   :toctree: ../stubs/

   NoiseLearnerOptions
   DynamicalDecouplingOptions
   ResilienceOptionsV2
   LayerNoiseLearningOptions
   MeasureNoiseLearningOptions
   PecOptions
   ZneOptions
   TwirlingOptions
   ExecutionOptionsV2
   SamplerExecutionOptionsV2
   EnvironmentOptions
   SimulatorOptions

"""

from .environment_options import EnvironmentOptions
from .execution_options import ExecutionOptionsV2
from .noise_learner_options import NoiseLearnerOptions
from .options import OptionsV2
from .simulator_options import SimulatorOptions
from .resilience_options import ResilienceOptionsV2
from .twirling_options import TwirlingOptions
from .estimator_options import EstimatorOptions
from .sampler_options import SamplerOptions
from .dynamical_decoupling_options import DynamicalDecouplingOptions
from .layer_noise_learning_options import LayerNoiseLearningOptions
from .measure_noise_learning_options import MeasureNoiseLearningOptions
from .pec_options import PecOptions
from .zne_options import ZneOptions
from .sampler_execution_options import SamplerExecutionOptionsV2
