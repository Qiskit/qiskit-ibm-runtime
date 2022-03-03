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

"""Estimator session"""

from typing import List, Optional, Union, Tuple, Any

from qiskit.primitives import EstimatorResult
from qiskit.primitives.base_estimator import Group

from .runtime_session import RuntimeSession


class EstimatorSession(RuntimeSession):
    """Estimator session"""

    def __call__(
        self,
        parameters: List[List[float]] = None,
        grouping: Optional[List[Union[Group, Tuple[int, int]]]] = None,
        **run_options: Any,
    ) -> EstimatorResult:
        self.write(parameters=parameters, grouping=grouping, run_options=run_options)
        raw_result = self.read()
        return EstimatorResult(raw_result["values"], raw_result["variances"])
