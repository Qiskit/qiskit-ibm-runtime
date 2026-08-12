# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests Executor based EstimatorV2 implementation using simulator through local mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from ddt import ddt
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.simulator import ExperimentalSimulatorOptions

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases

if TYPE_CHECKING:
    import numpy.typing as npt


@ddt
class TestEstimator(IBMTestCase):
    """Tests Executor based EstimatorV2 implementation using simulator through local mode."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = FakeManilaV2()
        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, target=self.backend.target
        )

    def test_trivials(self):
        circuit = QuantumCircuit(3)

        circuit.rx(np.pi/2, 1)
        circuit.ry(np.pi/2, 2)
        isa_circuit = self.preset_pass_manager.run(circuit)

        observables = [
                    SparsePauliOp(pauli_string).apply_layout(isa_circuit.layout)
                    for pauli_string in ["ZII", "IYI", "IIX"]
                ]

        parameters = []
        pub = (isa_circuit, observables, parameters)

        # Calculate ground truth to compare the results against via a statevector simulation:
        statevector_estimator = StatevectorEstimator()
        statevector_result = statevector_estimator.run([pub]).result()
        statevector_evs = statevector_result[0].data.evs

        print(f"statevector EVs: {statevector_evs}")