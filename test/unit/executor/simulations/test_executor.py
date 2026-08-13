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

"""Executor tests centered around qiskit-aer simulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from qiskit.primitives.containers import BitArray
from qiskit.quantum_info import Statevector, hellinger_fidelity
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from qiskit_ibm_runtime import Executor, QuantumProgram

if TYPE_CHECKING:
    from qiskit.circuit import QuantumCircuit

    from qiskit_ibm_runtime.results.quantum_program import QuantumProgramItemResult

from ....ibm_test_case import IBMTestCase
from ....utils import make_mirror_circuit_with_phases


class TestExecutor(IBMTestCase):
    """Executor tests centered around qiskit-aer simulations.

    All the tests in this class perform noiseless simulations.
    """

    def setUp(self):
        """Test level setup."""
        super().setUp()

        self.backend = AerSimulator()

        # The tolerance used when verifying simulated counts with exact probabilities via
        # Hellinger distance.
        self.tolerance = 0.01

    def verify_result(
        self,
        circuit: QuantumCircuit,
        parameter_values: np.ndarray,
        result: QuantumProgramItemResult,
    ) -> None:
        """A helper to verify the correctness of results.

        It computes the probabilities of each outcome exactly using Qiskit's StateVector class.
        Then, it compares them to the given ``counts`` via Hellinger distance.
        """
        circuit_cp = circuit.copy()
        circuit_cp.remove_final_measurements()

        array = result["meas"] ^ result["measurement_flips.meas"]
        for index in np.ndindex(parameter_values.shape[:-1]):
            assigned_parameters = parameter_values[index]
            bound_circuit = circuit_cp.assign_parameters(assigned_parameters)
            probabilities = Statevector(bound_circuit).probabilities_dict()
            self.assertAlmostEqual(
                fidelity := hellinger_fidelity(
                    BitArray.from_bool_array(array[index], order="little").get_counts(),
                    probabilities,
                ),
                1.0,
                msg=f"Fidelity: {fidelity}",
                delta=self.tolerance,
            )

    def test_simulation(self):
        """Test local mode simulations with the executor.

        Checks that:
        * The pub results match with the correct results.
        """
        circuit = make_mirror_circuit_with_phases(self.backend)

        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=0)
        pm.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True, enable_measures=True, add_tags="unique_box"
        )

        boxed_isa_circuit = pm.run(circuit)
        isa_template, samplex = build(boxed_isa_circuit)

        shape = (2, 4)
        parameter_values = np.random.random(shape + (circuit.num_parameters,))

        shots = 4_000
        program = QuantumProgram(shots=shots)
        program.append_samplex_item(
            isa_template, samplex=samplex, samplex_arguments={"parameter_values": parameter_values}
        )

        executor = Executor(mode=AerSimulator(), options={"experimental": {"local_mode": True}})

        job = executor.run(program)
        result = job.result()

        for qp_result in result:
            self.verify_result(circuit, parameter_values, qp_result)
