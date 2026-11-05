# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for job functions using real runtime service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qiskit_ibm_runtime.exceptions import RuntimeJobTimeoutError

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit_ibm_runtime import RuntimeJobV2


class TestIntegrationResults:
    """Integration tests for result callbacks."""

    def test_result_timeout(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job result timeout."""
        job = submit_bell_job()
        with pytest.raises(RuntimeJobTimeoutError):
            job.result(0.1)

    def test_wait_for_final_state_timeout(
        self, submit_bell_job: Callable[..., RuntimeJobV2]
    ) -> None:
        """Test job wait_for_final_state timeout."""
        job = submit_bell_job()
        with pytest.raises(RuntimeJobTimeoutError):
            job.wait_for_final_state(0.1)
