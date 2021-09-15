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
===========================================================
Job Manager (:mod:`qiskit_ibm.managed`)
===========================================================

.. currentmodule:: qiskit_ibm.managed

High level mechanism for handling jobs.

Classes
==========================
.. autosummary::
   :toctree: ../stubs/

   IBMJobManager
   ManagedJobSet
   ManagedJob
   ManagedResults

Exceptions
==========================
.. autosummary::
   :toctree: ../stubs/

   IBMJobManagerError
   IBMJobManagerInvalidStateError
   IBMJobManagerTimeoutError
   IBMJobManagerJobNotFound
   IBMManagedResultDataNotAvailable
   IBMJobManagerUnknownJobSet
"""

from .ibm_job_manager import IBMJobManager
from .managedjobset import ManagedJobSet
from .managedjob import ManagedJob
from .managedresults import ManagedResults
from .exceptions import *
