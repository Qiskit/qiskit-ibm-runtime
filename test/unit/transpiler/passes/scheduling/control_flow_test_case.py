# This code is part of Qiskit.
#
# (C) Copyright IBM 2022, 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Enhanced test case for control flow circuits."""

from typing import Any, Optional

from qiskit import QuantumCircuit
from qiskit.test._canonical import canonicalize_control_flow

from .....ibm_test_case import IBMTestCase


class ControlFlowTestCase(IBMTestCase):
    """Test case that enforces control flow canonicalization of quantum circuits."""

    def assertEqual(  # pylint: disable=arguments-differ
        self, first: Any, second: Any, msg: Optional[str] = None
    ) -> None:
        """Modify assertEqual to canonicalize the quantum circuit."""
        if isinstance(first, QuantumCircuit):
            first = canonicalize_control_flow(first)

        if isinstance(second, QuantumCircuit):
            second = canonicalize_control_flow(second)

        super().assertEqual(first, second, msg=msg)  # pylint: disable=no-value-for-parameter
