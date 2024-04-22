# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
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
from unittest import mock

from qiskit import transpile, qasm3, QuantumCircuit
from qiskit.circuit import IfElseOp
from qiskit.providers.models import (
    BackendStatus,
    BackendConfiguration,
    BackendProperties,
    PulseDefaults,
)

from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeManila, FakeSherbrooke
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.utils.backend_converter import convert_to_target

from ..ibm_test_case import IBMTestCase
from ..utils import (
    create_faulty_backend,
)


class TestBackend(IBMTestCase):
    """Tests for IBMBackend class."""

    def test_raise_faulty_qubits(self):
        """Test faulty qubits is raised."""
        fake_backend = FakeManila()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ.x(i)

        transpiled = transpile(circ, backend=fake_backend)
        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        sampler = SamplerV2(ibm_backend)

        with self.assertRaises(ValueError) as err:
            sampler.run([transpiled])

        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

    def test_raise_faulty_qubits_many(self):
        """Test faulty qubits is raised if one circuit uses it."""
        fake_backend = FakeManila()
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

        with self.assertRaises(ValueError) as err:
            sampler.run([transpiled])

        self.assertIn("inhomogeneous", str(err.exception))

    def test_raise_faulty_edge(self):
        """Test faulty edge is raised."""
        fake_backend = FakeManila()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits - 2):
            circ.cx(i, i + 1)

        transpiled = transpile(circ, backend=fake_backend)
        edge_qubits = [0, 1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))
        sampler = SamplerV2(ibm_backend)

        with self.assertRaises(ValueError) as err:
            sampler.run([transpiled])

        self.assertIn("cx", str(err.exception))
        self.assertIn(f"faulty edge {tuple(edge_qubits)}", str(err.exception))

    @staticmethod
    def test_faulty_qubit_not_used():
        """Test faulty qubit is not raise if not used."""
        fake_backend = FakeManila()
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

    @staticmethod
    def test_faulty_edge_not_used():
        """Test faulty edge is not raised if not used."""

        fake_backend = FakeManila()
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

    @staticmethod
    def _create_dc_test_backend():
        """Create a test backend with an IfElseOp enables."""
        model_backend = FakeManila()
        properties = model_backend.properties()

        out_backend = IBMBackend(
            configuration=model_backend.configuration(),
            service=mock.MagicMock(),
            api_client=None,
            instance=None,
        )

        out_backend.status = lambda: BackendStatus(
            backend_name="foo",
            backend_version="1.0",
            operational=True,
            pending_jobs=0,
            status_msg="",
        )
        out_backend.properties = lambda: properties

        return out_backend

    def test_single_dynamic_circuit_submission(self):
        """Test submitting single circuit with dynamic=True"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()
        sampler = SamplerV2(backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([circ])

        mock_run.assert_called_once()

    def test_multi_dynamic_circuit_submission(self):
        """Test submitting multiple circuits with dynamic=True"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()
        sampler = SamplerV2(backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        circuits = [circ, circ]

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run(circuits)

        mock_run.assert_called_once()

    def test_single_openqasm3_submission(self):
        """Test submitting a single openqasm3 strings with dynamic=True"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()
        sampler = SamplerV2(backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        qasm3_circ = qasm3.dumps(circ, disable_constants=True)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([qasm3_circ])

        mock_run.assert_called_once()

    def test_runtime_image_selection_submission(self):
        """Test image selection from runtime"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()
        sampler = SamplerV2(backend)

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        with mock.patch.object(SamplerV2, "run") as mock_run:
            sampler.run([circ])

        mock_run.assert_called_once()

    def test_deepcopy(self):
        """Test that deepcopy of a backend works properly"""
        backend = self._create_dc_test_backend()
        backend_copy = copy.deepcopy(backend)
        self.assertEqual(backend_copy.name, backend.name)

    def test_too_many_circuits(self):
        """Test exception when number of circuits exceeds backend._max_circuits"""
        model_backend = FakeManila()
        backend = IBMBackend(
            configuration=model_backend.configuration(),
            service=mock.MagicMock(),
            api_client=None,
            instance=None,
        )
        sampler = SamplerV2(backend)
        max_circs = backend.configuration().max_experiments

        circs = []
        for _ in range(max_circs + 1):
            circ = QuantumCircuit(1)
            circ.x(0)
            circs.append(circ)
        with self.assertRaises(ValueError) as err:
            sampler.run([circs])
        self.assertIn(
            f"{max_circs+1}",
            str(err.exception),
        )

    def test_control_flow_converter(self):
        """Test that control flow instructions are properly added to the target."""
        backend = FakeSherbrooke()
        backend._get_conf_dict_from_json()
        backend._set_props_dict_from_json()
        backend._set_defs_dict_from_json()
        target = convert_to_target(
            BackendConfiguration.from_dict(backend._conf_dict),
            BackendProperties.from_dict(backend._props_dict),
            PulseDefaults.from_dict(backend._defs_dict),
        )
        self.assertTrue(target.instruction_supported("if_else", ()))
        self.assertTrue(target.instruction_supported(operation_class=IfElseOp))
