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

"""Tests for Qiskit scheduling utilities."""

from qiskit_ibm_runtime.transpiler.passes.scheduling.utils import (
    DynamicCircuitInstructionDurations,
)
from qiskit_ibm_runtime.fake_provider import FakeKolkataV2
from .....ibm_test_case import IBMTestCase


class TestDynamicCircuitInstructionDurations(IBMTestCase):
    """Tests the DynamicCircuitInstructionDurations patching"""

    def test_durations_from_backend_v2(self):
        """Test loading and patching durations from a V2 Backend"""

        durations = DynamicCircuitInstructionDurations.from_backend(FakeKolkataV2())

        self.assertEqual(durations.get("x", (0,)), 160)
        self.assertEqual(durations.get("measure", (0,)), 3200)
        self.assertEqual(durations.get("reset", (0,)), 3200)

    def test_durations_from_target(self):
        """Test loading and patching durations from a target"""

        durations = DynamicCircuitInstructionDurations.from_target(FakeKolkataV2().target)

        self.assertEqual(durations.get("x", (0,)), 160)
        self.assertEqual(durations.get("measure", (0,)), 3200)
        self.assertEqual(durations.get("reset", (0,)), 3200)
