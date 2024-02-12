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

from typing import Dict
import numpy as np

from qiskit.primitives import EstimatorResult
from qiskit.primitives.containers import PrimitiveResult, make_data_bin, PubResult

from .result_decoder import ResultDecoder


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
                data_bin_cls = make_data_bin(
                    [("evs", np.ndarray), ("stds", np.ndarray)], shape=val.shape
                )
                out_results.append(
                    PubResult(data=data_bin_cls(val, meta.pop("standard_error")), metadata=meta)
                )
            # TODO what metadata should be passed in to PrimitiveResult?
            return PrimitiveResult(out_results, metadata=decoded["metadata"])
        return EstimatorResult(
            values=np.asarray(decoded["values"]),
            metadata=decoded["metadata"],
        )
