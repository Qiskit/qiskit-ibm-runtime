# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the classes used to instantiate noise learner results."""

from unittest import skipIf
from ddt import ddt

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit_aer import AerSimulator

from qiskit_ibm_runtime.fake_provider import FakeKyiv
from qiskit_ibm_runtime.utils.noise_learner_result import PauliLindbladError, LayerError

from ..ibm_test_case import IBMTestCase

try:
    import plotly.graph_objects as go

    PLOTLY_INSTALLED = True
except ImportError:
    PLOTLY_INSTALLED = False


class TestPauliLindbladError(IBMTestCase):
    """Class for testing the PauliLindbladError class."""

    def setUp(self):
        super().setUp()

        # A set of generators
        generators1 = PauliList(["X", "Z"])
        generators2 = PauliList(["XX", "ZZ", "IY"])
        self.generators = [generators1, generators2]

        # A set of rates
        rates1 = [0.1, 0.2]
        rates2 = [0.3, 0.4, 0.5]
        self.rates = [rates1, rates2]

    def test_valid_inputs(self):
        """Test PauliLindbladError with valid inputs."""
        for generators, rates in zip(self.generators, self.rates):
            error = PauliLindbladError(generators, rates)
            self.assertEqual(error.generators, generators)
            self.assertEqual(error.rates.tolist(), rates)
            self.assertEqual(error.num_qubits, generators.num_qubits)

    def test_invalid_inputs(self):
        """Test PauliLindbladError with invalid inputs."""
        with self.assertRaises(ValueError):
            PauliLindbladError(self.generators[0], self.rates[1])

    def test_json_roundtrip(self):
        """Tests a roundtrip with `_json`."""
        for generators, rates in zip(self.generators, self.rates):
            error1 = PauliLindbladError(generators, rates)
            error2 = PauliLindbladError(**error1._json())
            self.assertEqual(error1.generators, error2.generators)
            self.assertEqual(error1.rates.tolist(), error2.rates.tolist())

    def test_restrict_num_bodies(self):
        """Tests the ``restrict_num_bodies`` method."""
        generators = PauliList(["IIIX", "IIXI", "IXII", "YIII", "ZIII", "XXII", "ZZII"])
        rates = [0.01, 0.01, 0.01, 0.005, 0.02, 0.01, 0.01]
        error = PauliLindbladError(generators, rates)

        generators1 = PauliList(["IIIX", "IIXI", "IXII", "YIII", "ZIII"])
        rates1 = [0.01, 0.01, 0.01, 0.005, 0.02]
        error1 = PauliLindbladError(generators1, rates1)
        self.assertEqual(error.restrict_num_bodies(1).generators, error1.generators)
        self.assertEqual(error.restrict_num_bodies(1).rates.tolist(), error1.rates.tolist())

        generators2 = PauliList(["XXII", "ZZII"])
        rates2 = [0.01, 0.01]
        error2 = PauliLindbladError(generators2, rates2)
        self.assertEqual(error.restrict_num_bodies(2).generators, error2.generators)
        self.assertEqual(error.restrict_num_bodies(2).rates.tolist(), error2.rates.tolist())


@ddt
class TestLayerError(IBMTestCase):
    """Class for testing the LayerError class."""

    def setUp(self):
        super().setUp()

        # A set of circuits
        c1 = QuantumCircuit(2)
        c1.cx(0, 1)

        c2 = QuantumCircuit(3)
        c2.cx(0, 1)
        c2.cx(1, 2)

        self.circuits = [c1, c2]

        # A set of qubits
        qubits1 = [8, 9]
        qubits2 = [7, 11, 27]
        self.qubits = [qubits1, qubits2]

        # A set of errors
        error1 = PauliLindbladError(PauliList(["XX", "ZZ"]), [0.1, 0.2])
        error2 = PauliLindbladError(PauliList(["XXX", "ZZZ", "YIY"]), [0.3, 0.4, 0.5])
        error3 = None
        self.errors = [error1, error2, error3]

        # Another set of errors used in the visualization tests
        circuit = QuantumCircuit(4)
        qubits = [1, 2, 3, 4]
        generators = PauliList(["IIIX", "IIXI", "IXII", "YIII", "ZIII", "XXII", "ZZII"])
        rates = [0.01, 0.01, 0.01, 0.005, 0.02, 0.01, 0.01]
        self.layer_error_viz = LayerError(circuit, qubits, PauliLindbladError(generators, rates))

    def test_valid_inputs(self):
        """Test LayerError with valid inputs."""
        for circuit, qubits, error in zip(self.circuits, self.qubits, self.errors):
            layer_error = LayerError(circuit, qubits, error)
            self.assertEqual(layer_error.circuit, circuit)
            self.assertEqual(layer_error.qubits, qubits)
            self.assertEqual(layer_error.error, error)

            self.assertEqual(layer_error.num_qubits, circuit.num_qubits)
            self.assertEqual(layer_error.num_qubits, len(qubits))

    def test_invalid_inputs(self):
        """Test LayerError with invalid inputs."""
        with self.assertRaises(ValueError):
            LayerError(self.circuits[1], self.qubits[0], self.errors[0])

        with self.assertRaises(ValueError):
            LayerError(self.circuits[0], self.qubits[1], self.errors[0])

        with self.assertRaises(ValueError):
            LayerError(self.circuits[0], self.qubits[0], self.errors[1])

    def test_json_roundtrip(self):
        """Tests a roundtrip with `_json`."""
        for circuit, qubits, error in zip(self.circuits, self.qubits, self.errors):
            layer_error1 = LayerError(circuit, qubits, error)
            layer_error2 = LayerError(**layer_error1._json())
            self.assertEqual(layer_error1.circuit, layer_error2.circuit)
            self.assertEqual(layer_error1.qubits, layer_error2.qubits)
            self.assertEqual(layer_error1.error, layer_error2.error)

    @skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_no_coupling_map(self):
        r"""
        Tests the `draw_map` function with invalid coordinates.
        """
        with self.assertRaises(ValueError):
            self.layer_error_viz.draw_map(AerSimulator())

    @skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_plotting(self):
        r"""
        Tests the `draw_map` function to make sure that it produces the right figure.
        """
        fig = self.layer_error_viz.draw_map(
            embedding=FakeKyiv(),
            color_no_data="blue",
            colorscale="reds",
            radius=0.2,
            width=500,
            height=200,
        )

        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 160)
