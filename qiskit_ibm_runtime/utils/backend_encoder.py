# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utilities for working with IBM Quantum backends."""
import json
from datetime import datetime
from typing import Any

from qiskit.circuit import ParameterExpression


class BackendEncoder(json.JSONEncoder):
    """A json encoder for qobj"""

    def default(self, obj: Any) -> Any:  # pylint: disable=arguments-differ
        """Default encoding"""
        # Convert numpy arrays:
        if hasattr(obj, "tolist"):
            return obj.tolist()
        # Use Qobj complex json format:
        if isinstance(obj, complex):
            return [obj.real, obj.imag]
        if isinstance(obj, ParameterExpression):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)
