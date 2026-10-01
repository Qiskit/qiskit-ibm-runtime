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

"""Tests for the functions used to visualize noise learner results."""

from unittest import skipUnless

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit.utils.optionals import HAS_AER

from qiskit_ibm_runtime.fake_provider import FakeKyiv
from qiskit_ibm_runtime.results.noise_learner import LayerError, PauliLindbladError
from qiskit_ibm_runtime.visualization import draw_layer_error_map, draw_layer_errors_swarm

from .case import IBMVisualizationTestCase

if HAS_AER:
    from qiskit_aer import AerSimulator


def layer_errors():
    """Return three layer errors, acting on two, three, and four qubits."""
    circuits = [QuantumCircuit(2), QuantumCircuit(3), QuantumCircuit(4)]

    qubits = [[8, 9], [7, 11, 27], [1, 8, 9, 10]]

    errors = [
        PauliLindbladError(PauliList(["XX", "ZZ"]), [0.1, 0.2]),
        PauliLindbladError(PauliList(["XXX", "ZZZ", "YIY"]), [0.3, 0.4, 0.5]),
        PauliLindbladError(
            PauliList(["IIIX", "IIXI", "IXII", "YIII", "ZIII", "XXII", "ZZII"]),
            [0.01, 0.01, 0.01, 0.005, 0.02, 0.01, 0.01],
        ),
    ]

    return [
        LayerError(circuit, layer_qubits, error)
        for circuit, layer_qubits, error in zip(circuits, qubits, errors)
    ]


class TestDrawLayerErrorMap(IBMVisualizationTestCase):
    """Class for testing the ``draw_layer_error_map`` function."""

    def test_plotting(self):
        """Test to make sure that it produces the right figure."""
        errors = layer_errors()
        fig = draw_layer_error_map(
            errors[2],
            embedding=FakeKyiv(),
            color_no_data="blue",
            colorscale="reds",
            radius=0.2,
            width=1000,
            height=1000,
        )

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]
        self.assertEqual(len(data), 160)
        self.assertEqual(layout["height"], 1000)
        self.assertEqual(layout["width"], 1000)

        self.save_plotly_artifact(fig)

    @skipUnless(condition=HAS_AER, reason="qiskit-aer is required to run this test")
    def test_no_coupling_map(self):
        """Test error when invalid coordinates are passed."""
        errors = layer_errors()
        with self.assertRaises(ValueError):
            draw_layer_error_map(errors[0], AerSimulator())


class TestDrawLayerErrorsSwarm(IBMVisualizationTestCase):
    """Class for testing the ``draw_layer_errors_swarm`` function."""

    def test_plotting(self):
        """Test that it produces the right image."""
        errors = layer_errors()
        fig = draw_layer_errors_swarm(
            errors,
            colors=["red", "blue", "green"],
            names=["l1", "l2", "l3"],
            width=1000,
            height=800,
        )

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]

        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["name"], "l1")
        self.assertEqual(data[1]["name"], "l2")
        self.assertEqual(data[2]["name"], "l3")

        self.assertEqual(
            layout["xaxis"],
            {
                "title": {"text": "layers"},
                "range": [-1, 3],
                "ticktext": ["l1", "l2", "l3"],
                "tickvals": [0, 1, 2],
                "showgrid": False,
                "zeroline": False,
            },
        )
        self.assertEqual(layout["yaxis"], {"title": {"text": "rates"}})
        self.assertEqual(layout["width"], 1000)
        self.assertEqual(layout["height"], 800)

        self.save_plotly_artifact(fig)

    def test_errors(self):
        """Test errors."""
        errors = layer_errors()

        with self.assertRaisesRegex(ValueError, "Expected 3 colors"):
            draw_layer_errors_swarm(errors, colors=["blue", "red"])

        with self.assertRaisesRegex(ValueError, "Expected 3 names"):
            draw_layer_errors_swarm(errors, names=["names1", "names2"])

        with self.assertRaisesRegex(ValueError, "Expected 3 opacities"):
            draw_layer_errors_swarm(errors, opacities=[0.1, 0.2])
