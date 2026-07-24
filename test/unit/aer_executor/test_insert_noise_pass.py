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

"""Tests for InsertNoisePass."""

import warnings
from unittest import skipUnless

import numpy as np
from ddt import data, ddt, unpack
from qiskit.circuit import Barrier, QuantumCircuit
from qiskit.quantum_info import DensityMatrix, PauliLindbladMap
from qiskit.transpiler import PassManager
from qiskit.utils import optionals

from ...ibm_test_case import IBMTestCase

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator

    from qiskit_ibm_runtime.aer_executor.insert_noise_pass import InsertNoisePass


def _circuit_with_barrier(n_qubits: int, label: str) -> QuantumCircuit:
    circuit = QuantumCircuit(n_qubits)
    circuit.append(Barrier(n_qubits, label=label), list(range(n_qubits)))
    return circuit


def _noise_error_ops(circuit: QuantumCircuit) -> list:
    # PauliLindbladError is wrapped in QuantumChannelInstruction when going through the DAG.
    return [instr.operation for instr in circuit.data if instr.operation.name == "quantum_channel"]


@ddt
@skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
class TestInsertNoisePass(IBMTestCase):
    """Tests for InsertNoisePass."""

    @data((True, "R", 1), (True, "M", 0), (False, "R", 0), (False, "M", 1))
    @unpack
    def test_noise_after_true_injects_at_r_barriers(
        self, noise_after, barrier_type, num_noise_error_ops
    ):
        """Test `noise_after` for different types of barriers."""
        inject_noise = InsertNoisePass(
            noise_dict={"r0": PauliLindbladMap.from_list([("XI", 0.1), ("IX", 0.2)])},
            noise_after=noise_after,
        )
        pm = PassManager([inject_noise])
        result = pm.run(_circuit_with_barrier(2, label=f"{barrier_type}0@tag=r0"))
        self.assertEqual(len(_noise_error_ops(result)), num_noise_error_ops)

    def test_noise_scale_multiplies_rates(self):
        """Test the `noise_scale` argument."""
        circuit = _circuit_with_barrier(2, "R0@tag=r0")
        noise_dict = {"r0": PauliLindbladMap.from_list([("XI", 0.1)])}

        pm_1x = PassManager([InsertNoisePass(noise_dict=noise_dict, noise_scale=1.0)])
        result_1x = pm_1x.run(circuit)

        pm_3x = PassManager([InsertNoisePass(noise_dict=noise_dict, noise_scale=3.0)])
        result_3x = pm_3x.run(circuit)

        # PauliLindbladError is stored as ._quantum_error inside QuantumChannelInstruction.
        np.testing.assert_allclose(_noise_error_ops(result_1x)[0]._quantum_error.rates, [0.1])  # noqa: SLF001
        np.testing.assert_allclose(_noise_error_ops(result_3x)[0]._quantum_error.rates, [0.3])  # noqa: SLF001

    def test_warn_absent(self):
        """Test the ``warn_absent`` field."""
        circuit = _circuit_with_barrier(2, "R0@tag=unknown")
        noise_dict = {"r0": PauliLindbladMap.from_list([("XI", 0.1)])}

        with self.assertWarnsRegex(UserWarning, "No noise found for tag 'unknown'"):
            PassManager([InsertNoisePass(noise_dict=noise_dict, warn_absent=True)]).run(circuit)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            PassManager([InsertNoisePass(noise_dict=noise_dict, warn_absent=False)]).run(circuit)

    def test_none_noise_dict_is_noop(self):
        """Test that ``noise_dict=None`` is a noop."""
        circuit = _circuit_with_barrier(2, "R0@tag=r0")
        result = PassManager([InsertNoisePass(noise_dict=None)]).run(circuit)
        self.assertEqual(len(_noise_error_ops(result)), 0)

    def test_missing_tag_leaves_barrier_intact(self):
        """Test that missing tags leave barriers intect."""
        circuit = _circuit_with_barrier(2, "R0@tag=unknown")
        noise_dict = {"r0": PauliLindbladMap.from_list([("XI", 0.1)])}

        pm = PassManager([InsertNoisePass(noise_dict=noise_dict, warn_absent=False)])
        result = pm.run(circuit)

        self.assertEqual(len(_noise_error_ops(result)), 0)
        self.assertEqual(result.count_ops().get("barrier", 0), 1)

    def test_noise_qubits_ordered_by_physical_index(self):
        """Test qubit order."""
        # Barrier on a non-canonical qubit subset/order: qargs = [2, 0].  After substitution the
        # PauliLindbladError must land on physical qubits [0, 2] (ascending), not [2, 0].
        circuit = QuantumCircuit(3)
        circuit.append(Barrier(2, label="R0@tag=r0"), [2, 0])

        noise_dict = {"r0": PauliLindbladMap.from_list([("XI", 0.1)])}
        result = PassManager([InsertNoisePass(noise_dict=noise_dict, noise_after=True)]).run(
            circuit
        )

        noise_instrs = [instr for instr in result.data if instr.operation.name == "quantum_channel"]
        self.assertEqual(len(noise_instrs), 1)
        self.assertEqual([result.find_bit(q).index for q in noise_instrs[0].qubits], [0, 2])
        # The original barrier should appear exactly once--regression: an earlier fix duplicated it.
        self.assertEqual(result.count_ops().get("barrier", 0), 1)

    @data("order", [[0, 1, 3], [3, 0, 1], [0, 3, 1]])
    def test_noise_simulation_applies_rates_to_correct_physical_qubits(self, order):
        """Test correct physical qubits are selected."""
        # We want to inject this noise on qubits {0, 1, 3}. We set the barrier qubits to [3, 0, 1]
        # just to prove that we ignore the barrier qubit order, and instead use the order of the
        # physical qubits. In this case we should get
        #   "IIX" rate 0.20 -> X on physical qubit 0
        #   "IXI" rate 0.10 -> X on physical qubit 1
        #   "XII" rate 0.05 -> X on physical qubit 3
        noise_dict = {
            "r0": PauliLindbladMap.from_list([("IIX", 0.20), ("IXI", 0.10), ("XII", 0.05)])
        }

        circuit = QuantumCircuit(4)
        circuit.append(Barrier(3, label="R0@tag=r0"), [3, 0, 1])

        noisy = PassManager([InsertNoisePass(noise_dict=noise_dict, noise_after=True)]).run(circuit)
        noisy.save_density_matrix()

        result = AerSimulator(method="density_matrix").run(noisy).result()
        dm = DensityMatrix(result.data(0)["density_matrix"])

        rates_per_physical_qubit = np.array([0.20, 0.10, 0.0, 0.05])
        expected_p1 = (1 - np.exp(-2 * rates_per_physical_qubit)) / 2
        actual_p1 = np.array([dm.probabilities([q])[1] for q in range(circuit.num_qubits)])
        np.testing.assert_allclose(actual_p1, expected_p1, atol=1e-10)
