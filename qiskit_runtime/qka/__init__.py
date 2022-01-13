# This code is part of qiskit-runtime.
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
Quantum Kernel Alignment modules
================================

.. currentmodule:: qiskit_runtime.qka

Aux files
---------

The ``aux_file`` directory contains datasets for binary classification.

KernelMatrix class
------------------

.. autosummary::
   :toctree: ../stubs/

    KernelMatrix

FeatureMap class
------------------

.. autosummary::
   :toctree: ../stubs/

    FeatureMap

"""

from .kernel_matrix import KernelMatrix
from .featuremaps import FeatureMap
