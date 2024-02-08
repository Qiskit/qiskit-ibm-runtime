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
import warnings

from qiskit import transpile, qasm3, QuantumCircuit
from qiskit.providers.models import BackendStatus

from qiskit_ibm_runtime.exceptions import IBMBackendValueError
from qiskit_ibm_runtime.fake_provider import FakeManila
from qiskit_ibm_runtime.ibm_backend import IBMBackend

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

        with self.assertRaises(ValueError) as err:
            ibm_backend.run(transpiled)

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

        with self.assertRaises(ValueError) as err:
            ibm_backend.run(transpiled)

        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

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

        with self.assertRaises(ValueError) as err:
            ibm_backend.run(transpiled)

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

        with mock.patch.object(IBMBackend, "_runtime_run") as mock_run:
            ibm_backend.run(circuits=transpiled)

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

        with mock.patch.object(IBMBackend, "_runtime_run") as mock_run:
            ibm_backend.run(circuits=transpiled)

        mock_run.assert_called_once()

    def test_dynamic_circuits_warning(self):
        """Test warning when user defines dynamic==False and circuits are dynamic"""
        # pylint: disable=not-context-manager

        # backend is not faulty because no faulty parameters given
        backend = create_faulty_backend(model_backend=FakeManila())

        circuits = []
        circ = QuantumCircuit(2, 2)
        circ.h(0)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)
        circuits.append(circ)

        circ = QuantumCircuit(3, 2)
        with circ.for_loop(range(4)):
            circ.h(0)
        circuits.append(circ)

        circ = QuantumCircuit(2, 2)
        circ.h(0)
        circ.measure([0], [0])
        with circ.switch(target=0) as case:
            with case(0):
                circ.x(0)
            with case(case.DEFAULT):
                circ.cx(0, 1)
        circuits.append(circ)

        for circuit in circuits:
            # using warnings to catch multiple warnings
            with warnings.catch_warnings(record=True) as warn:
                with mock.patch.object(IBMBackend, "_runtime_run"):
                    backend.run(circuits=circuit, dynamic=False)
            self.assertIn(
                "Parameter 'dynamic' is False, but the circuit contains dynamic constructs.",
                str(warn[0].message),
            )
            self.assertIn(
                f"The backend {backend.name} does not support dynamic circuits.",
                str(warn[1].message),
            )

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

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        with mock.patch.object(IBMBackend, "_runtime_run") as mock_run:
            backend.run(circuits=circ, dynamic=True)

        mock_run.assert_called_once()

    def test_multi_dynamic_circuit_submission(self):
        """Test submitting multiple circuits with dynamic=True"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        circuits = [circ, circ]

        with mock.patch.object(IBMBackend, "_runtime_run") as mock_run:
            backend.run(circuits=circuits, dynamic=True)

        mock_run.assert_called_once()

    def test_single_openqasm3_submission(self):
        """Test submitting a single openqasm3 strings with dynamic=True"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        qasm3_circ = qasm3.dumps(circ, disable_constants=True)

        with mock.patch.object(IBMBackend, "_runtime_run") as mock_run:
            backend.run(circuits=qasm3_circ, dynamic=True)

        mock_run.assert_called_once()

    def test_runtime_image_selection_submission(self):
        """Test image selection from runtime"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        with mock.patch.object(IBMBackend, "_runtime_run") as mock_run:
            backend.run(circuits=circ, dynamic=True)

        mock_run.assert_called_once()

    def test_multi_openqasm3_submission(self):
        """Test submitting multiple openqasm3 strings with dynamic=True"""
        # pylint: disable=not-context-manager

        backend = self._create_dc_test_backend()

        circ = QuantumCircuit(2, 2)
        circ.measure(0, 0)
        with circ.if_test((0, False)):
            circ.x(1)

        image = "test-image"

        with mock.patch.object(IBMBackend, "_runtime_run") as mock_run:
            backend.run(circuits=circ, dynamic=True, image=image)

        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args.kwargs["image"], image)

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
        max_circs = backend.configuration().max_experiments

        circs = []
        for _ in range(max_circs + 1):
            circ = QuantumCircuit(1)
            circ.x(0)
            circs.append(circ)
        with self.assertRaises(IBMBackendValueError) as err:
            backend.run(circs)
        self.assertIn(
            f"Number of circuits, {max_circs+1} exceeds the maximum for this backend, {max_circs}",
            str(err.exception),
        )
