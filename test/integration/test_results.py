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

"""Tests for job functions using real runtime service."""


from qiskit_ibm_runtime.exceptions import RuntimeJobTimeoutError

from ..ibm_test_case import IBMIntegrationJobTestCase
from ..decorators import run_integration_test


class TestIntegrationResults(IBMIntegrationJobTestCase):
    """Integration tests for result callbacks."""

    @run_integration_test
    def test_result_timeout(self, service):
        """Test job result timeout"""
        job = self._run_program(service)
        with self.assertRaises(RuntimeJobTimeoutError):
            job.result(0.1)

    @run_integration_test
    def test_wait_for_final_state_timeout(self, service):
        """Test job wait_for_final_state timeout"""
        job = self._run_program(service)
        with self.assertRaises(RuntimeJobTimeoutError):
            job.wait_for_final_state(0.1)
