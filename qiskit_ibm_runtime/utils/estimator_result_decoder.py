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

"""Estimator result decoder."""

from typing import Dict, List
import numpy as np

from qiskit.primitives import EstimatorResult

from ..program.result_decoder import ResultDecoder
from ..qiskit.primitives.task_result import TaskResult


class EstimatorResultDecoder(ResultDecoder):
    """Class used to decode estimator results"""

    @classmethod
    def decode(  # type: ignore # pylint: disable=arguments-differ
        cls, raw_result: str, version: int
    ) -> EstimatorResult:
        """Convert the result to EstimatorResult."""
        decoded: Dict = super().decode(raw_result)
        if version == 2:
            out_results = []
            for val, meta in zip(decoded["values"], decoded["metadata"]):
                if not isinstance(val, np.ndarray):
                    val = np.asarray(val)
                out_results.append(
                    TaskResult(data={"evs": val, "stds": meta.pop("standard_error")}, metadata=meta)
                )
            return out_results
        return EstimatorResult(
            values=np.asarray(decoded["values"]),
            metadata=decoded["metadata"],
        )
