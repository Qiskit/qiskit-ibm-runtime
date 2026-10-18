# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test folding Rzz angle into calibrated range."""

from itertools import chain
from math import pi

import numpy as np
import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.parameter import Parameter
from qiskit.quantum_info import Operator, SparsePauliOp
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import EstimatorV2, SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend
from qiskit_ibm_runtime.transpiler.passes.basis.fold_rzz_angle import (
    FoldRzzAngle,
    convert_to_rzz_valid_pub,
)
from qiskit_ibm_runtime.utils.utils import is_isa_circuit, is_valid_rzz_pub


class TestFoldRzzAngle:
    """Test FoldRzzAngle pass."""

    @pytest.mark.parametrize(
        "angle",
        [
            pi / 2,
            -pi / 2,
            pi,
            -pi,
            0.1,
            pi / 2 + 0.1,
            -pi + 0.1,
            -0.1,
            2 * pi + 0.1,
            -3 * pi / 2 + 0.1,
            pi + 0.1,
            2 * pi - 0.1,
            -12 * pi + 0.1,
            23 * pi / 2 + 0.1,
            11 * pi + 0.1,
            -12 * pi - 0.1,
            # Odd-winding multiples of pi that wrap exactly onto the +-pi boundary. These drop
            # an odd number of 2*pi windings, so the folded circuit must re-add a global phase
            # of pi to remain unitary-equivalent (not merely equivalent up to global phase).
            3 * pi,
            -3 * pi,
            7 * pi,
            -7 * pi,
            5 * pi,
            -5 * pi,
        ],
        ids=[
            "pi/2_pos",
            "pi/2_neg",
            "pi_pos",
            "pi_neg",
            "quad1_no_wrap",
            "quad2_no_wrap",
            "quad3_no_wrap",
            "quad4_no_wrap",
            "quad1_2pi_wrap",
            "quad2_2pi_wrap",
            "quad3_2pi_wrap",
            "quad4_2pi_wrap",
            "quad1_12pi_wrap",
            "quad2_12pi_wrap",
            "quad3_12pi_wrap",
            "quad4_12pi_wrap",
            "3pi_pos",
            "3pi_neg",
            "7pi_pos",
            "7pi_neg",
            "5pi_pos",
            "5pi_neg",
        ],
    )
    def test_folding_rzz_angles(self, angle: float) -> None:
        """Test folding gate angle into calibrated range."""
        qc = QuantumCircuit(2)
        qc.rzz(angle, 0, 1)
        pm = PassManager([FoldRzzAngle()])
        isa = pm.run(qc)

        assert Operator.from_circuit(qc) == Operator.from_circuit(isa)
        assert set(isa.count_ops()).issubset({"rzz", "cz", "rz", "sx", "x", "rx"})
        for inst_data in isa.data:
            if inst_data.operation.name == "rzz":
                fold_angle = inst_data.operation.params[0]
                assert fold_angle >= 0.0
                assert fold_angle <= pi / 2

    @pytest.mark.parametrize(
        "angle",
        [
            pi / 2,
            -pi / 2,
            pi,
            -pi,
            0.1,
            pi / 2 + 0.1,
            -pi + 0.1,
            -0.1,
            2 * pi + 0.1,
            -3 * pi / 2 + 0.1,
            pi + 0.1,
            2 * pi - 0.1,
            -12 * pi + 0.1,
            23 * pi / 2 + 0.1,
            11 * pi + 0.1,
            -12 * pi - 0.1,
            # Odd-winding multiples of pi that wrap exactly onto the +-pi boundary. These drop
            # an odd number of 2*pi windings, so the folded circuit must re-add a global phase
            # of pi to remain unitary-equivalent (not merely equivalent up to global phase).
            3 * pi,
            -3 * pi,
            7 * pi,
            -7 * pi,
            5 * pi,
            -5 * pi,
        ],
        ids=[
            "pi/2_pos",
            "pi/2_neg",
            "pi_pos",
            "pi_neg",
            "quad1_no_wrap",
            "quad2_no_wrap",
            "quad3_no_wrap",
            "quad4_no_wrap",
            "quad1_2pi_wrap",
            "quad2_2pi_wrap",
            "quad3_2pi_wrap",
            "quad4_2pi_wrap",
            "quad1_12pi_wrap",
            "quad2_12pi_wrap",
            "quad3_12pi_wrap",
            "quad4_12pi_wrap",
            "3pi_pos",
            "3pi_neg",
            "7pi_pos",
            "7pi_neg",
            "5pi_pos",
            "5pi_neg",
        ],
    )
    def test_rzz_folding_with_wrap_registry(self, angle: float) -> None:
        """Test angle folding when done through Qiskit's built in angle bounds mechanism."""
        qc = QuantumCircuit(2)
        qc.rzz(angle, 0, 1)
        backend = FakeFractionalBackend()

        pm = generate_preset_pass_manager(
            optimization_level=2,
            backend=backend,
        )
        isa = pm.run(qc)
        # By default the generated backend should register the angle wrapping
        # function when angle bounds are set.
        assert backend.target.gate_has_angle_bounds("rzz")
        assert is_isa_circuit(isa, backend.target) == ""
        for inst_data in isa.data:
            if inst_data.operation.name == "rzz":
                fold_angle = inst_data.operation.params[0]
                assert fold_angle >= 0.0
                assert fold_angle <= pi / 2

    def test_folding_rzz_angle_unbound(self) -> None:
        """Test skip folding unbound gate angle."""
        qc = QuantumCircuit(2)
        qc.rzz(Parameter("θ"), 0, 1)
        pm = PassManager([FoldRzzAngle()])
        isa = pm.run(qc)
        assert qc == isa

    def test_controlflow(self) -> None:
        """Test non-ISA Rzz gates inside/outside a control flow branch."""
        qc = QuantumCircuit(2, 1)
        qc.rzz(-0.2, 0, 1)
        with qc.if_test((0, 1)):
            qc.rzz(-0.1, 0, 1)
            with qc.if_test((0, 1)):
                qc.rzz(-0.3, 0, 1)

        pm = PassManager([FoldRzzAngle()])
        isa = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.rzz(0.2, 0, 1)
        expected.x(0)
        with expected.if_test((0, 1)):
            expected.x(0)
            expected.rzz(0.1, 0, 1)
            expected.x(0)
            with expected.if_test((0, 1)):
                expected.x(0)
                expected.rzz(0.3, 0, 1)
                expected.x(0)

        assert isa == expected

    @pytest.mark.parametrize("rzz_angle", [-1, -1 + 4 * np.pi])
    def test_fractional_plugin(self, rzz_angle: float) -> None:
        """Verify that a pass manager for a fractional backend applies the rzz folding pass."""
        circ = QuantumCircuit(2)
        circ.rzz(rzz_angle, 0, 1)
        backend = FakeFractionalBackend()

        pm = generate_preset_pass_manager(
            optimization_level=2,
            backend=backend,
            translation_method="ibm_dynamic_circuits",
        )
        isa_circ = pm.run(circ)

        assert is_isa_circuit(isa_circ, backend.target) == ""
        assert len(isa_circ.data) == 3
        assert isa_circ.data[1].operation.name == "rzz"
        assert np.isclose(isa_circ.data[1].operation.params[0], 1)

    @pytest.mark.parametrize(
        ("p1_set1", "p2_set1", "p1_set2", "p2_set2", "expected_num_params"),
        [
            [0.2, 0.1, 0.4, 0.3, 2],  # no modification in circuit
            [0.2, 0.1, 0.3, 0.4, 4],  # rzz_2_rx with values 0 and pi
            [0.1, 0.2, 0.3, 0.4, 3],  # x
            [0.2, 0.1, 0.3, 2, 7],  # rzz_1_rx, rzz_1_rz, rzz_2_rz with values 0 and pi
            [0.3, 2, 0.3, 2, 4],  # circuit changes but no new parameters
        ],
    )
    def test_rzz_pub_conversion(
        self,
        p1_set1: float,
        p2_set1: float,
        p1_set2: float,
        p2_set2: float,
        expected_num_params: int,
    ) -> None:
        """Test the function `convert_to_rzz_valid_circ_and_vals`."""
        p1 = Parameter("p1")
        p2 = Parameter("p2")

        circ = QuantumCircuit(3)
        circ.rzz(p1 + p2, 0, 1)
        circ.rzz(0.3, 0, 1)
        circ.x(0)
        circ.rzz(p1 - p2, 2, 1)

        param_vals_arr = np.array([[[p1_set1, p2_set1]], [[p1_set2, p2_set2]]])
        isa_pub = convert_to_rzz_valid_pub(
            SamplerV2(FakeFractionalBackend()), (circ, param_vals_arr)
        )

        isa_param_vals = isa_pub.parameter_values
        assert isa_param_vals.num_parameters == expected_num_params
        assert is_valid_rzz_pub(isa_pub) == ""

        param_flat = param_vals_arr.reshape(-1, param_vals_arr.shape[-1])
        isa_flat = isa_param_vals.ravel().as_array()
        for param_set_1, param_set_2 in zip(param_flat, isa_flat):
            assert Operator.from_circuit(circ.assign_parameters(param_set_1)).equiv(
                Operator.from_circuit(isa_pub.circuit.assign_parameters(param_set_2))
            )

    @pytest.mark.skip(reason="convert_to_rzz_valid_pub does not support dynamic circuits currently")
    def test_rzz_pub_conversion_dynamic(self) -> None:
        """Test the function `convert_to_rzz_valid_circ_and_vals` for dynamic circuits."""
        p = Parameter("p")
        observable = SparsePauliOp("ZZZ")

        circ = QuantumCircuit(3, 1)
        with circ.if_test((0, 1)):
            circ.rzz(p, 1, 2)
            circ.rzz(p, 1, 2)
        circ.rzz(p, 0, 1)
        with circ.if_test((0, 1)):
            circ.rzz(p, 1, 0)
            circ.rzz(p, 1, 0)
        circ.rzz(p, 0, 1)

        isa_pub = convert_to_rzz_valid_pub(
            EstimatorV2(FakeFractionalBackend()), (circ, observable, [1, -1])
        )
        assert is_valid_rzz_pub(isa_pub) == ""
        assert [observable] == isa_pub.observables

        # TODO: test qubit indices
        isa_pub_param_names = np.array(list(chain.from_iterable(isa_pub.parameter_values.data)))
        assert len(isa_pub_param_names) == 6
        for param_name in [
            "rzz_block1_rx1",
            "rzz_block1_rx2",
            "rzz_rx1",
            "rzz_block2_rx1",
            "rzz_block2_rx2",
            "rzz_rx2",
        ]:
            assert param_name in isa_pub_param_names
