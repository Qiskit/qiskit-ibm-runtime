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

"""IBM module for Estimator primitive"""

from typing import List, Tuple, Optional, Union, Dict

from qiskit.circuit import QuantumCircuit
from qiskit.primitives.base_estimator import Group
from qiskit.quantum_info import SparsePauliOp

from .base_primitive import BasePrimitive
from .sessions.estimator_session import EstimatorSession


class IBMEstimator(BasePrimitive):
    """IBM module for Estimator primitive"""

    def __call__(  # type: ignore[override]
        self,
        circuits: List[QuantumCircuit],
        observables: List[SparsePauliOp],
        grouping: Optional[List[Union[Group, Tuple[int, int]]]] = None,
        transpile_options: Optional[Dict] = None,
    ) -> EstimatorSession:
        # pylint: disable=arguments-differ
        inputs = {
            "circuits": circuits,
            "observables": observables,
            "grouping": grouping,
            "transpile_options": transpile_options,
        }

        options = {}
        if self._backend:
            options["backend_name"] = self._backend

        return EstimatorSession(
            runtime=self._service,
            program_id="estimator",
            inputs=inputs,
            options=options,
        )
