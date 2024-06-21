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
from qiskit_ibm_runtime.fake_provider import FakeKolkata, FakeKolkataV2
from .....ibm_test_case import IBMTestCase


class TestDynamicCircuitInstructionDurations(IBMTestCase):
    """Tests the DynamicCircuitInstructionDurations patching"""

    def test_patch_measure(self):
        """Test if schedules circuits with c_if after measure with a common clbit.
        See: https://github.com/Qiskit/qiskit-terra/issues/7654"""

        durations = DynamicCircuitInstructionDurations(
            [
                ("x", None, 200),
                ("sx", (0,), 200),
                ("measure", None, 1000),
                ("measure", (0, 1), 1200),
                ("reset", None, 800),
            ]
        )

        self.assertEqual(durations.get("x", (0,)), 200)
        self.assertEqual(durations.get("measure", (0,)), 1160)
        self.assertEqual(durations.get("measure", (0, 1)), 1360)
        self.assertEqual(durations.get("reset", (0,)), 1160)

        short_odd_durations = DynamicCircuitInstructionDurations(
            [
                ("sx", (0,), 112),
                ("measure", None, 1000),
                ("reset", None, 800),
            ]
        )

        self.assertEqual(short_odd_durations.get("measure", (0,)), 1224)
        self.assertEqual(short_odd_durations.get("reset", (0,)), 1224)

    def test_durations_from_backend_v1(self):
        """Test loading and patching durations from a V1 Backend"""

        durations = DynamicCircuitInstructionDurations.from_backend(FakeKolkata())

        self.assertEqual(durations.get("x", (0,)), 160)
        self.assertEqual(durations.get("measure", (0,)), 3200)
        self.assertEqual(durations.get("reset", (0,)), 3200)

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

    def test_patch_disable(self):
        """Test if schedules circuits with c_if after measure with a common clbit.
        See: https://github.com/Qiskit/qiskit-terra/issues/7654"""

        durations = DynamicCircuitInstructionDurations(
            [("x", None, 200), ("measure", None, 1000), ("measure", (0, 1), 1200)],
            enable_patching=False,
        )

        self.assertEqual(durations.get("x", (0,)), 200)
        self.assertEqual(durations.get("measure", (0,)), 1000)
        self.assertEqual(durations.get("measure", (0, 1)), 1200)
