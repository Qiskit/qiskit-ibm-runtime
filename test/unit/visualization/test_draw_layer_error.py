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

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit_aer import AerSimulator

from qiskit_ibm_runtime.fake_provider import FakeKyiv
from qiskit_ibm_runtime.utils.noise_learner_result import PauliLindbladError, LayerError
from qiskit_ibm_runtime.visualization import (
    draw_layer_error_map,
    draw_layer_error_1q_bar_plot,
    draw_layer_error_2q_bar_plot,
    draw_layer_errors_swarm,
)

from ...ibm_test_case import IBMTestCase

try:
    import plotly.graph_objects as go

    PLOTLY_INSTALLED = True
except ImportError:
    PLOTLY_INSTALLED = False


class DrawLayerErrorBase(IBMTestCase):
    """Base class for testing the functions that draw layer errors."""

    def setUp(self):
        super().setUp()

        # A set of circuits
        c1 = QuantumCircuit(2)
        c2 = QuantumCircuit(3)
        c3 = QuantumCircuit(4)
        self.circuits = [c1, c2, c3]

        # A set of qubits
        qubits1 = [8, 9]
        qubits2 = [7, 11, 27]
        qubits3 = [1, 8, 9, 10]
        self.qubits = [qubits1, qubits2, qubits3]

        # A set of errors
        error1 = PauliLindbladError(PauliList(["XX", "ZZ"]), [0.1, 0.2])
        error2 = PauliLindbladError(PauliList(["XXX", "ZZZ", "YIY"]), [0.3, 0.4, 0.5])
        error3 = PauliLindbladError(
            PauliList(["IIIX", "IIXI", "IXII", "YIII", "ZIII", "XXII", "ZZII"]),
            [0.01, 0.01, 0.01, 0.005, 0.02, 0.01, 0.01],
        )
        self.errors = [error1, error2, error3]

        # A set of layer errors
        layer_error1 = LayerError(c1, qubits1, error1)
        layer_error2 = LayerError(c2, qubits2, error2)
        layer_error3 = LayerError(c3, qubits3, error3)
        self.layer_errors = [layer_error1, layer_error2, layer_error3]


@skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
class TestDrawLayerErrorMap(DrawLayerErrorBase):
    """Class for testing the ``draw_layer_error_map`` function."""

    def test_plotting(self):
        r"""
        Test to make sure that it produces the right figure.
        """
        fig = draw_layer_error_map(
            self.layer_errors[2],
            embedding=FakeKyiv(),
            color_no_data="blue",
            colorscale="reds",
            radius=0.2,
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]
        self.assertEqual(len(data), 160)
        self.assertEqual(layout["height"], 200)
        self.assertEqual(layout["width"], 500)

    def test_no_coupling_map(self):
        r"""
        Test error when invalid coordinates are passed.
        """
        with self.assertRaises(ValueError):
            draw_layer_error_map(self.layer_errors[0], AerSimulator())


@skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
class TestDraw1QBarPlot(DrawLayerErrorBase):
    """Class for testing the ``draw_layer_error_1q_bar_plot`` function."""

    def test_plotting_qubit(self):
        r"""
        Test with ``grouping`` set to ``qubit``.
        """
        fig = draw_layer_error_1q_bar_plot(
            self.layer_errors[2],
            grouping="qubit",
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]

        self.assertEqual(len(data), 4)
        self.assertEqual(data[0]["x"], ["X_1"])
        self.assertEqual(data[1]["x"], ["X_8"])
        self.assertEqual(data[2]["x"], ["X_9"])
        self.assertEqual(data[3]["x"], ["Y_10", "Z_10"])
        self.assertEqual(set(d["type"] for d in data), {"bar"})

        self.assertEqual(layout["xaxis"], {"title": {"text": "generators"}})
        self.assertEqual(layout["yaxis"], {"title": {"text": "rates"}})
        self.assertEqual(layout["width"], 500)
        self.assertEqual(layout["height"], 200)

    def test_plotting_generator(self):
        r"""
        Test with ``grouping`` set to ``generator``.
        """
        fig = draw_layer_error_1q_bar_plot(
            self.layer_errors[2],
            grouping="generator",
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]

        self.assertEqual(len(data), 4)
        self.assertEqual(data[0]["x"], ["X"])
        self.assertEqual(data[1]["x"], ["X"])
        self.assertEqual(data[2]["x"], ["X"])
        self.assertListEqual(list(data[3]["x"]), ["Y", "Z"])
        self.assertEqual(set(d["type"] for d in data), {"bar"})

        self.assertEqual(layout["xaxis"], {"title": {"text": "generators"}})
        self.assertEqual(layout["yaxis"], {"title": {"text": "rates"}})
        self.assertEqual(layout["width"], 500)
        self.assertEqual(layout["height"], 200)

    def test_filter_by_qubit(self):
        r"""
        Test with ``qubits`` not set to ``None``.
        """
        fig = draw_layer_error_1q_bar_plot(
            self.layer_errors[2],
            grouping="generator",
            qubits=self.layer_errors[2].qubits[:2],
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["x"], ["X"])
        self.assertEqual(data[1]["x"], ["X"])
        self.assertEqual(set(d["type"] for d in data), {"bar"})

        self.assertEqual(layout["xaxis"], {"title": {"text": "generators"}})
        self.assertEqual(layout["yaxis"], {"title": {"text": "rates"}})
        self.assertEqual(layout["width"], 500)
        self.assertEqual(layout["height"], 200)

    def test_filter_by_generator(self):
        r"""
        Test with ``generators`` not set to ``None``.
        """
        fig = draw_layer_error_1q_bar_plot(
            self.layer_errors[2],
            grouping="generator",
            generators=["X"],
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]

        self.assertEqual(len(data), 4)
        self.assertEqual(data[0]["x"], ["X"])
        self.assertEqual(data[1]["x"], ["X"])
        self.assertEqual(data[2]["x"], ["X"])
        self.assertEqual(list(data[3]["x"]), [])
        self.assertEqual(set(d["type"] for d in data), {"bar"})

        self.assertEqual(layout["xaxis"], {"title": {"text": "generators"}})
        self.assertEqual(layout["yaxis"], {"title": {"text": "rates"}})
        self.assertEqual(layout["width"], 500)
        self.assertEqual(layout["height"], 200)

    def test_errors(self):
        r"""
        Test errors.
        """
        with self.assertRaisesRegex(ValueError, "Grouping 'invalid grouping'"):
            draw_layer_error_1q_bar_plot(self.layer_errors[0], grouping="invalid grouping")

        with self.assertRaisesRegex(ValueError, "Expected 2 colors"):
            draw_layer_error_1q_bar_plot(self.layer_errors[0], colors=["blue"])


@skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
class TestDraw2QBarPlot(DrawLayerErrorBase):
    """Class for testing the ``draw_layer_error_2q_bar_plot`` function."""

    def test_plotting_qubit(self):
        r"""
        Test with ``grouping`` set to ``edge``.
        """
        fig = draw_layer_error_2q_bar_plot(
            self.layer_errors[2],
            grouping="edge",
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "edge: (9, 10)")
        self.assertListEqual(list(data[0]["x"]), ["XX_9,10", "ZZ_9,10"])

        self.assertEqual(layout["xaxis"], {"title": {"text": "generators"}})
        self.assertEqual(layout["yaxis"], {"title": {"text": "rates"}})
        self.assertEqual(layout["width"], 500)
        self.assertEqual(layout["height"], 200)

    def test_plotting_generator(self):
        r"""
        Test with ``grouping`` set to ``generator``.
        """
        fig = draw_layer_error_2q_bar_plot(
            self.layer_errors[2],
            grouping="generator",
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

        fig_d = fig.to_dict()
        data = fig_d["data"]
        layout = fig_d["layout"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "edge: (9, 10)")
        self.assertListEqual(list(data[0]["x"]), ["XX", "ZZ"])
        self.assertEqual(data[0]["type"], "bar")

        self.assertEqual(layout["xaxis"], {"title": {"text": "generators"}})
        self.assertEqual(layout["yaxis"], {"title": {"text": "rates"}})
        self.assertEqual(layout["width"], 500)
        self.assertEqual(layout["height"], 200)

    def test_errors(self):
        r"""
        Test errors.
        """
        with self.assertRaisesRegex(ValueError, "Grouping 'invalid grouping'"):
            draw_layer_error_2q_bar_plot(self.layer_errors[0], grouping="invalid grouping")

        with self.assertRaisesRegex(ValueError, "Expected 1 colors"):
            draw_layer_error_2q_bar_plot(self.layer_errors[0], colors=["blue", "red"])


@skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
class TestDrawLayerErrorsSwarm(DrawLayerErrorBase):
    """Class for testing the ``draw_layer_errors_swarm`` function."""

    def test_plotting(self):
        r"""
        Test that it produces the right image.
        """
        fig = draw_layer_errors_swarm(
            self.layer_errors,
            colors=["red", "blue", "green"],
            names=["l1", "l2", "l3"],
            width=500,
            height=200,
        )
        self.assertIsInstance(fig, go.Figure)

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
        self.assertEqual(layout["width"], 500)
        self.assertEqual(layout["height"], 200)

    def test_errors(self):
        r"""
        Test errors.
        """
        with self.assertRaisesRegex(ValueError, "Expected 3 colors"):
            draw_layer_errors_swarm(self.layer_errors, colors=["blue", "red"])

        with self.assertRaisesRegex(ValueError, "Expected 3 names"):
            draw_layer_errors_swarm(self.layer_errors, names=["names1", "names2"])

        with self.assertRaisesRegex(ValueError, "Expected 3 opacities"):
            draw_layer_errors_swarm(self.layer_errors, opacities=[0.1, 0.2])
