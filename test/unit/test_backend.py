# This code is part of Qiskit.
#
# (C) Copyright IBM 2023-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the backend functions."""

import copy
from typing import cast
from unittest import mock

import pytest
from qiskit import QuantumCircuit, qasm3, transpile
from qiskit.circuit import ForLoopOp, IfElseOp, Reset, SwitchCaseOp, WhileLoopOp
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.circuit import MidCircuitMeasure
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend, FakeManilaV2, FakeSherbrooke
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.models import BackendConfiguration, BackendProperties, BackendStatus
from qiskit_ibm_runtime.utils.backend_converter import convert_to_target

from ..utils import create_faulty_backend
from .mock.fake_backends import FakeMidcircuit


@pytest.fixture
def dynamic_circuits_backend() -> IBMBackend:
    """Create a test backend with an IfElseOp enables."""
    model_backend = FakeManilaV2()
    properties = model_backend.properties()

    out_backend = IBMBackend(
        configuration=model_backend.configuration(),
        service=mock.MagicMock(),
        api_client=None,
        instance=None,
    )

    out_backend.status = lambda: BackendStatus(  # type: ignore[method-assign]
        backend_name="foo",
        backend_version="1.0",
        operational=True,
        pending_jobs=0,
        status_msg="",
    )
    out_backend.properties = lambda: properties  # type: ignore[method-assign, misc, assignment]

    return out_backend


def assert_props(
    backend: IBMBackend, name: str, ref_error: float | None, ref_duration: float | None
) -> None:
    """Assert that all instruction properties for ``name`` have the given error and duration."""
    for _, props in backend.target[name].items():
        error = props.error if props else None
        duration = props.duration if props else None
        assert error == ref_error
        assert duration == ref_duration


class TestBackend:
    """Tests for IBMBackend class."""

    def test_raise_faulty_qubits(self) -> None:
        """Test faulty qubits is raised."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ.x(i)

        transpiled = transpile(circ, backend=fake_backend)
        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        sampler = SamplerV2(ibm_backend)

        with pytest.raises(ValueError) as err:
            sampler.run([transpiled])

        assert f"faulty qubit {faulty_qubit}" in str(err.value)

    def test_raise_faulty_qubits_many(self) -> None:
        """Test faulty qubits is raised if one circuit uses it."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits

        circ1 = QuantumCircuit(1, 1)
        circ1.x(0)
        circ2 = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ2.x(i)

        transpiled = transpile([circ1, circ2], backend=fake_backend)
        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        sampler = SamplerV2(ibm_backend)

        with pytest.raises(ValueError) as err:
            sampler.run(transpiled)

        assert "faulty" in str(err.value)

    def test_raise_faulty_edge(self) -> None:
        """Test faulty edge is raised."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits - 2):
            circ.cx(i, i + 1)

        transpiled = transpile(circ, backend=fake_backend, optimization_level=1)
        edge_qubits = [0, 1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))
        sampler = SamplerV2(ibm_backend)

        with pytest.raises(ValueError) as err:
            sampler.run([transpiled])

        assert "cx" in str(err.value)
        assert f"faulty edge {tuple(edge_qubits)}" in str(err.value)

    def test_faulty_qubit_not_used(self) -> None:
        """Test faulty qubit is not raise if not used."""
        fake_backend = FakeManilaV2()
        circ = QuantumCircuit(2, 2)
        for i in range(2):
            circ.x(i)

        transpiled = transpile(circ, backend=fake_backend, initial_layout=[0, 1])
        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        sampler = SamplerV2(ibm_backend)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([transpiled])

        mock_run.assert_called_once()

    def test_faulty_edge_not_used(self) -> None:
        """Test faulty edge is not raised if not used."""
        fake_backend = FakeManilaV2()
        coupling_map = fake_backend.configuration().coupling_map

        circ = QuantumCircuit(2, 2)
        circ.cx(0, 1)

        transpiled = transpile(circ, backend=fake_backend, initial_layout=coupling_map[0])
        edge_qubits = coupling_map[-1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))
        sampler = SamplerV2(ibm_backend)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([transpiled])

        mock_run.assert_called_once()

    def test_single_dynamic_circuit_submission(self, dynamic_circuits_backend: IBMBackend) -> None:
        """Test submitting single circuit with dynamic=True."""
        sampler = SamplerV2(dynamic_circuits_backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([circ])

        mock_run.assert_called_once()

    def test_multi_dynamic_circuit_submission(self, dynamic_circuits_backend: IBMBackend) -> None:
        """Test submitting multiple circuits with dynamic=True."""
        sampler = SamplerV2(dynamic_circuits_backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        circuits = [circ, circ]

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run(circuits)

        mock_run.assert_called_once()

    def test_single_openqasm3_submission(self, dynamic_circuits_backend: IBMBackend) -> None:
        """Test submitting a single openqasm3 strings with dynamic=True."""
        sampler = SamplerV2(dynamic_circuits_backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        qasm3_circ = qasm3.dumps(circ, disable_constants=True)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([qasm3_circ])

        mock_run.assert_called_once()

    def test_runtime_image_selection_submission(self, dynamic_circuits_backend: IBMBackend) -> None:
        """Test image selection from runtime."""
        sampler = SamplerV2(dynamic_circuits_backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([circ])

        mock_run.assert_called_once()

    def test_deepcopy(self, dynamic_circuits_backend: IBMBackend) -> None:
        """Test that deepcopy of a dynamic_circuits_backend works properly."""
        backend_copy = copy.deepcopy(dynamic_circuits_backend)
        assert backend_copy.name == dynamic_circuits_backend.name

    def test_control_flow_converter(self) -> None:
        """Test that control flow instructions are properly added to the target."""
        backend = FakeSherbrooke()
        backend._get_conf_dict_from_json()
        backend._set_props_dict_from_json()
        target = convert_to_target(
            BackendConfiguration.from_dict(backend._conf_dict),
            BackendProperties.from_dict(backend._props_dict),
        )
        assert target.instruction_supported("if_else", ())
        assert target.instruction_supported(operation_class=IfElseOp)
        assert not target.instruction_supported("while_loop", ())
        assert not target.instruction_supported(operation_class=WhileLoopOp)
        assert target.instruction_supported("for_loop", ())
        assert target.instruction_supported(operation_class=ForLoopOp)
        assert target.instruction_supported("switch_case", ())
        assert target.instruction_supported(operation_class=SwitchCaseOp)

    def test_reset(self) -> None:
        """Test that reset instruction is properly added to the target."""
        backend = FakeSherbrooke()
        backend._get_conf_dict_from_json()
        backend._set_props_dict_from_json()
        target = convert_to_target(
            BackendConfiguration.from_dict(backend._conf_dict),
            BackendProperties.from_dict(backend._props_dict),
        )
        assert target.instruction_supported("reset")
        assert target.instruction_supported(operation_class=Reset)

    def test_non_unitary_isa_operations(self) -> None:
        """Test handling of non-unitary ISA operations."""
        target = convert_to_target(cast("BackendConfiguration", FakeSherbrooke().configuration()))

        assert isinstance(target.get("reset"), dict)
        assert isinstance(target.get("measure"), dict)
        assert target.get("measure_2") is None

    def test_convert_to_target_with_filter(self) -> None:
        """Test converting legacy data structure to V2 target model with faulty qubits.

        Measure and Delay are automatically added to the output Target
        even though instruction is not provided by the backend,
        since these are the necessary instructions that the transpiler may assume.
        """
        # Filter out faulty Q1
        fake_backend = FakeManilaV2()
        faulty_qubit = 1
        faulty_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        target = convert_to_target(
            configuration=cast("BackendConfiguration", faulty_backend.configuration()),
            properties=faulty_backend.properties(),
        )
        assert not target.instruction_supported(operation_name="measure", qargs=(1,))
        assert not target.instruction_supported(operation_name="delay", qargs=(1,))

    def test_convert_to_target(self) -> None:
        """Test converting legacy data structure to V2 target model with missing qubit property."""
        fake_backend = FakeManilaV2()
        faulty_qubit = 1
        faulty_backend = create_faulty_backend(fake_backend, faulty_q1_property=faulty_qubit)
        target = convert_to_target(
            configuration=cast("BackendConfiguration", faulty_backend.configuration()),
            properties=faulty_backend.properties(),
        )

        assert target.qubit_properties[1].t1 is None
        assert target.qubit_properties[1].t2 == faulty_backend.properties().t2(1)
        assert target.qubit_properties[1].frequency == faulty_backend.properties().frequency(1)

    @pytest.mark.parametrize(
        "options",
        [[True, True], [True, False], [False, True], [False, False]],
        ids=[
            "with_dynamic_with_fractional",
            "with_dynamic_without_fractional",
            "without_dynamic_with_fractional",
            "without_dynamic_without_fractional",
        ],
    )
    def test_convert_to_target_with_features(self, options: list[bool]) -> None:
        """Test converting into Target model with selective features."""
        use_dynamic, use_fractional = options
        backend = FakeFractionalBackend()
        backend._set_props_dict_from_json()
        configuration = BackendConfiguration.from_dict(backend._conf_dict)
        properties = BackendProperties.from_dict(backend._props_dict)

        target = convert_to_target(
            configuration=configuration,
            properties=properties,
            include_control_flow=use_dynamic,
            include_fractional_gates=use_fractional,
        )

        assert ("rx" in target) == use_fractional
        assert ("rzz" in target) == use_fractional
        assert ("rx" in target.operation_names) == use_fractional
        assert ("rzz" in target.operation_names) == use_fractional
        assert ("if_else" in target.operation_names) == use_dynamic
        assert ("while_loop" in target.operation_names) == use_dynamic

    def test_instruction_signatures(self) -> None:
        """Test building a target with alternative instruction signatures in its configuration."""
        backend = FakeMidcircuit()

        assert set(backend.basis_gates) == {"id", "rz", "sx", "x", "cx"}
        assert set(backend.operation_names) == {
            "id",
            "cx",
            "sx",
            "rz",
            "delay",
            "measure",
            "measure_2",
            "x",
            "reset",
            "reset_2",
            "reset_3",
            "alternative_rx",
        }
        assert_props(backend, "measure_2", 3.142, None)
        assert_props(backend, "reset_2", None, 3.142e-08)

        # Test transpilation with FakeMidcircuit
        mcm = MidCircuitMeasure()
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 2)
        qc.append(mcm, [0], [0])
        transpiled = pm.run(qc)
        assert transpiled.data[0].operation.name == "measure_2"
