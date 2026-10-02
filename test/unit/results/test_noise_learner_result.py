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

"""Tests for the classes used to instantiate noise learner results."""

from unittest import skipIf, skipUnless

from ddt import ddt
from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit.utils.optionals import HAS_AER

from qiskit_ibm_runtime.fake_provider import FakeKyiv
from qiskit_ibm_runtime.results.noise_learner import LayerError, PauliLindbladError

from ...ibm_test_case import IBMTestCase

try:
    import plotly.graph_objects as go

    PLOTLY_INSTALLED = True
except ImportError:
    PLOTLY_INSTALLED = False

if HAS_AER:
    from qiskit_aer import AerSimulator


def generators_and_rates():
    """Return a set of generators and their rates, for one and for two qubits."""
    generators = [PauliList(["X", "Z"]), PauliList(["XX", "ZZ", "IY"])]
    rates = [[0.1, 0.2], [0.3, 0.4, 0.5]]

    return generators, rates


class TestPauliLindbladError(IBMTestCase):
    """Class for testing the PauliLindbladError class."""

    def test_valid_inputs(self):
        """Test PauliLindbladError with valid inputs."""
        all_generators, all_rates = generators_and_rates()

        for generators, rates in zip(all_generators, all_rates):
            error = PauliLindbladError(generators, rates)
            self.assertEqual(error.generators, generators)
            self.assertEqual(error.rates.tolist(), rates)
            self.assertEqual(error.num_qubits, generators.num_qubits)

    def test_invalid_inputs(self):
        """Test PauliLindbladError with invalid inputs."""
        all_generators, all_rates = generators_and_rates()

        with self.assertRaises(ValueError):
            PauliLindbladError(all_generators[0], all_rates[1])

    def test_json_roundtrip(self):
        """Tests a roundtrip with `_json`."""
        all_generators, all_rates = generators_and_rates()

        for generators, rates in zip(all_generators, all_rates):
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


def circuits_qubits_and_errors():
    """Return a set of circuits, the qubits they act on, and their errors.

    The last error is `None`, to cover layer errors without one.
    """
    c1 = QuantumCircuit(2)
    c1.cx(0, 1)

    c2 = QuantumCircuit(3)
    c2.cx(0, 1)
    c2.cx(1, 2)

    circuits = [c1, c2]

    qubits = [[8, 9], [7, 11, 27]]

    errors = [
        PauliLindbladError(PauliList(["XX", "ZZ"]), [0.1, 0.2]),
        PauliLindbladError(PauliList(["XXX", "ZZZ", "YIY"]), [0.3, 0.4, 0.5]),
        None,
    ]

    return circuits, qubits, errors


def layer_error_to_draw():
    """Return a four-qubit layer error, with both one-body and two-body generators."""
    circuit = QuantumCircuit(4)
    qubits = [1, 2, 3, 4]
    generators = PauliList(["IIIX", "IIXI", "IXII", "YIII", "ZIII", "XXII", "ZZII"])
    rates = [0.01, 0.01, 0.01, 0.005, 0.02, 0.01, 0.01]

    return LayerError(circuit, qubits, PauliLindbladError(generators, rates))


@ddt
class TestLayerError(IBMTestCase):
    """Class for testing the LayerError class."""

    def test_valid_inputs(self):
        """Test LayerError with valid inputs."""
        circuits, all_qubits, errors = circuits_qubits_and_errors()

        for circuit, qubits, error in zip(circuits, all_qubits, errors):
            layer_error = LayerError(circuit, qubits, error)
            self.assertEqual(layer_error.circuit, circuit)
            self.assertEqual(layer_error.qubits, qubits)
            self.assertEqual(layer_error.error, error)

            self.assertEqual(layer_error.num_qubits, circuit.num_qubits)
            self.assertEqual(layer_error.num_qubits, len(qubits))

    def test_invalid_inputs(self):
        """Test LayerError with invalid inputs."""
        circuits, qubits, errors = circuits_qubits_and_errors()

        with self.assertRaises(ValueError):
            LayerError(circuits[1], qubits[0], errors[0])

        with self.assertRaises(ValueError):
            LayerError(circuits[0], qubits[1], errors[0])

        with self.assertRaises(ValueError):
            LayerError(circuits[0], qubits[0], errors[1])

    def test_json_roundtrip(self):
        """Tests a roundtrip with `_json`."""
        circuits, all_qubits, errors = circuits_qubits_and_errors()

        for circuit, qubits, error in zip(circuits, all_qubits, errors):
            layer_error1 = LayerError(circuit, qubits, error)
            layer_error2 = LayerError(**layer_error1._json())
            self.assertEqual(layer_error1.circuit, layer_error2.circuit)
            self.assertEqual(layer_error1.qubits, layer_error2.qubits)
            self.assertEqual(layer_error1.error, layer_error2.error)

    @skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    @skipUnless(condition=HAS_AER, reason="qiskit-aer is required to run this test")
    def test_no_coupling_map(self):
        """Tests the `draw_map` function with invalid coordinates."""
        with self.assertRaises(ValueError):
            layer_error_to_draw().draw_map(AerSimulator())

    @skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_plotting(self):
        """Tests the `draw_map` function to make sure that it produces the right figure."""
        fig = layer_error_to_draw().draw_map(
            embedding=FakeKyiv(),
            color_no_data="blue",
            colorscale="reds",
            radius=0.2,
            width=500,
            height=200,
        )

        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 160)
