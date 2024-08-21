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

"""Tests for the noise learner."""

import json
import os
from ddt import ddt, data

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit_aer import AerSimulator

from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime.visualization import draw_layer_error_map
from qiskit_ibm_runtime.visualization.utils import get_qubits_coordinates

from qiskit_ibm_runtime.utils.noise_learner_result import LayerError, PauliLindbladError

from ...ibm_test_case import IBMTestCase


@ddt
class TestDrawLayerErrorMap(IBMTestCase):
    """Class for testing the draw_layer_error_map function."""

    def setUp(self):
        super().setUp()

        # A local service
        self.service = QiskitRuntimeLocalService()

        # A layer error
        circuit = QuantumCircuit(4)
        qubits = [0, 1, 2, 3]
        generators = PauliList(["IIIX", "IIXI", "IXII", "YIII", "ZIII", "XXII", "ZZII"])
        rates = [0.01, 0.01, 0.01, 0.005, 0.02, 0.01, 0.01]
        error = PauliLindbladError(generators, rates)
        self.layer_error = LayerError(circuit, qubits, error)

        # Whether or not assets should be regenerated
        self.regenerate_assets = False

        # The path to the assets
        self.assets_path = os.path.dirname(os.path.realpath(__file__)) + "/assets/"

    def test_invalid_coordinates(self):
        r"""
        Tests the plotting function with invalid coordinates.
        """
        backend = self.service.backend("fake_kyiv")
        coordinates = get_qubits_coordinates(backend.num_qubits)[:10]

        with self.assertRaises(ValueError):
            draw_layer_error_map(self.layer_error, backend, coordinates)

    def test_no_coupling_map(self):
        r"""
        Tests the plotting function with invalid coordinates.
        """
        with self.assertRaises(ValueError):
            draw_layer_error_map(self.layer_error, AerSimulator())

    @data("fake_hanoi", "fake_kyiv")
    def test_plotting(self, backend_name):
        r"""
        Tests the plotting function to make sure that it produces the right figure.
        """
        backend = self.service.backend(backend_name)
        fig = draw_layer_error_map(
            self.layer_error,
            backend,
            color_no_data="blue",
            colorscale="reds",
            radius=0.2,
            width=500,
            height=200,
        )

        file = self.assets_path + f"draw_layer_error_map_{backend_name}.json"
        if self.regenerate_assets:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(fig.to_json(), f)

        with open(file, "r", encoding="utf-8") as f:
            self.assertEqual(fig.to_json(), json.load(f))
