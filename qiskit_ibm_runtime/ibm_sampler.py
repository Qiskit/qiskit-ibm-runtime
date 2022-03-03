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

"""IBM module for Sampler primitive"""

from typing import Optional, List, Dict

from qiskit.circuit import QuantumCircuit

from .base_primitive import BasePrimitive
from .sessions.sampler_session import SamplerSession


class IBMSampler(BasePrimitive):
    """IBM module for Sampler primitive"""

    def __call__(  # type: ignore[override]
        self,
        circuits: List[QuantumCircuit],
        transpile_options: Optional[Dict] = None,
        skip_transpilation: bool = False,
    ) -> SamplerSession:
        # pylint: disable=arguments-differ
        inputs = {
            "circuits": circuits,
            "transpile_options": transpile_options,
            "skip_transpilation": skip_transpilation,
        }

        options = {}
        if self._backend:
            options["backend_name"] = self._backend

        return SamplerSession(
            runtime=self._service,
            program_id="sampler",
            inputs=inputs,
            options=options,
        )
