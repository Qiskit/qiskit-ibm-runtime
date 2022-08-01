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

"""Tests for Sampler class."""

from unittest.mock import MagicMock

from qiskit_ibm_runtime import Session, Sampler
from ..ibm_test_case import IBMTestCase


class TestPrograms(IBMTestCase):
    """Class for testing runtime modules."""

    def test_sampler_new_session_old_call(self):
        """Test calling sampler with new session."""
        with Session(service=MagicMock()) as session:
            sampler = session.sampler()
            with self.assertRaises(ValueError):
                sampler(circuits=MagicMock())

    def test_sampler_old_session_new_call(self):
        """Test old session with new run method."""
        with Sampler(service=MagicMock()) as sampler:
            with self.assertRaises(ValueError):
                sampler.run(circuits=MagicMock())
