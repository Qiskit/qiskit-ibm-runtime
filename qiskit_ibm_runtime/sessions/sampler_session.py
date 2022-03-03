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

"""Sampler session"""

from typing import Optional, Union, List, Any

from qiskit.primitives import SamplerResult

from .runtime_session import RuntimeSession


class SamplerSession(RuntimeSession):
    """Sampler session"""

    def __call__(
        self,
        parameters: Optional[Union[List[float], List[List[float]]]] = None,
        **run_options: Any
    ) -> SamplerResult:
        self.write(parameters=parameters, run_options=run_options)
        raw_result = self.read()
        return SamplerResult(
            quasi_dists=raw_result["quasi_dists"],
            shots=raw_result["shots"],
            raw_results=None,
            metadata=None,
        )
