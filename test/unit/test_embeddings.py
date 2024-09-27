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

"""Tests for the ``Embedding`` class."""

from qiskit_aer import AerSimulator

from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime.utils.embeddings import Embedding, _get_qubits_coordinates

from ..ibm_test_case import IBMTestCase


class TestEmbedding(IBMTestCase):
    """Class for testing the Embedding class."""

    def setUp(self):
        super().setUp()

        service = QiskitRuntimeLocalService()
        self.aer = AerSimulator()
        self.kyiv = service.backend("fake_kyiv")
        self.vigo = service.backend("fake_vigo")
        self.armonk = service.backend("fake_armonk")

    def test_from_backend(self):
        r"""Test the constructor from backend."""
        e = Embedding.from_backend(self.vigo)

        coo = [(1, 0), (0, 1), (1, 1), (1, 2), (2, 1)]
        self.assertEqual(e.coordinates, coo)
        self.assertEqual(e.coupling_map, self.vigo.coupling_map)

    def test_init_error(self):
        r"""Test the errors raised by the constructor."""
        e_vigo = Embedding.from_backend(self.vigo)
        e_kyiv = Embedding.from_backend(self.kyiv)

        with self.assertRaisesRegex(
            ValueError, "Coupling map for backend 'aer_simulator' is unknown."
        ):
            Embedding.from_backend(self.aer)

        with self.assertRaisesRegex(ValueError, "Invalid coupling map."):
            Embedding(e_vigo.coordinates, e_kyiv.coupling_map)

        with self.assertRaisesRegex(ValueError, "Failed to fetch coordinates for backend"):
            Embedding.from_backend(self.armonk)


class TestGetCoordinates(IBMTestCase):
    """Class for testing the `_get_qubits_coordinates` function."""

    def test_5(self):
        r"""Test for 5-qubit lattices."""
        exp = [(1, 0), (0, 1), (1, 1), (1, 2), (2, 1)]
        self.assertListEqual(_get_qubits_coordinates(5), exp)

    def test_7(self):
        r"""Test for 7-qubit lattices."""
        exp = [(0, 0), (0, 1), (0, 2), (1, 1), (2, 0), (2, 1), (2, 2)]
        self.assertListEqual(_get_qubits_coordinates(7), exp)

    def test_15(self):
        r"""Test for 15-qubit lattices."""
        exp = [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (1, 7),
            (1, 6),
            (1, 5),
            (1, 4),
            (1, 3),
            (1, 2),
            (1, 1),
            (1, 0),
        ]
        self.assertListEqual(_get_qubits_coordinates(15), exp)

    def test_16(self):
        r"""Test for 16-qubit lattices."""
        exp = [
            (1, 0),
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 2),
            (3, 2),
            (0, 3),
            (1, 3),
            (3, 3),
            (4, 3),
            (1, 4),
            (3, 4),
            (1, 5),
            (2, 5),
            (3, 5),
            (1, 6),
        ]
        self.assertListEqual(_get_qubits_coordinates(16), exp)

    def test_20(self):
        r"""Test for 20-qubit lattices."""
        exp = [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
            (1, 4),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (3, 0),
            (3, 1),
            (3, 2),
            (3, 3),
            (3, 4),
        ]
        self.assertListEqual(_get_qubits_coordinates(20), exp)

    def test_27(self):
        r"""Test for 27-qubit lattices."""
        exp = [
            (1, 0),
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 2),
            (3, 2),
            (0, 3),
            (1, 3),
            (3, 3),
            (4, 3),
            (1, 4),
            (3, 4),
            (1, 5),
            (2, 5),
            (3, 5),
            (1, 6),
            (3, 6),
            (0, 7),
            (1, 7),
            (3, 7),
            (4, 7),
            (1, 8),
            (3, 8),
            (1, 9),
            (2, 9),
            (3, 9),
            (3, 10),
        ]
        self.assertListEqual(_get_qubits_coordinates(27), exp)

    def test_28(self):
        r"""Test for 28-qubit lattices."""
        exp = [
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (1, 2),
            (1, 6),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (3, 0),
            (3, 4),
            (3, 8),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
        ]
        self.assertListEqual(_get_qubits_coordinates(28), exp)

    def test_53(self):
        r"""Test for 53-qubit lattices."""
        exp = [
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (1, 2),
            (1, 6),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (3, 0),
            (3, 4),
            (3, 8),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
            (5, 2),
            (5, 6),
            (6, 0),
            (6, 1),
            (6, 2),
            (6, 3),
            (6, 4),
            (6, 5),
            (6, 6),
            (6, 7),
            (6, 8),
            (7, 0),
            (7, 4),
            (7, 8),
            (8, 0),
            (8, 1),
            (8, 2),
            (8, 3),
            (8, 4),
            (8, 5),
            (8, 6),
            (8, 7),
            (8, 8),
            (9, 2),
            (9, 6),
        ]
        self.assertListEqual(_get_qubits_coordinates(53), exp)

    def test_65(self):
        r"""Test for 65-qubit lattices."""
        exp = [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (0, 7),
            (0, 8),
            (0, 9),
            (1, 0),
            (1, 4),
            (1, 8),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (2, 9),
            (2, 10),
            (3, 2),
            (3, 6),
            (3, 10),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
            (4, 9),
            (4, 10),
            (5, 0),
            (5, 4),
            (5, 8),
            (6, 0),
            (6, 1),
            (6, 2),
            (6, 3),
            (6, 4),
            (6, 5),
            (6, 6),
            (6, 7),
            (6, 8),
            (6, 9),
            (6, 10),
            (7, 2),
            (7, 6),
            (7, 10),
            (8, 1),
            (8, 2),
            (8, 3),
            (8, 4),
            (8, 5),
            (8, 6),
            (8, 7),
            (8, 8),
            (8, 9),
            (8, 10),
        ]
        self.assertListEqual(_get_qubits_coordinates(65), exp)

    def test_127(self):
        r"""Test for 127-qubit lattices."""
        exp = [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (0, 7),
            (0, 8),
            (0, 9),
            (0, 10),
            (0, 11),
            (0, 12),
            (0, 13),
            (1, 0),
            (1, 4),
            (1, 8),
            (1, 12),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (2, 9),
            (2, 10),
            (2, 11),
            (2, 12),
            (2, 13),
            (2, 14),
            (3, 2),
            (3, 6),
            (3, 10),
            (3, 14),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
            (4, 9),
            (4, 10),
            (4, 11),
            (4, 12),
            (4, 13),
            (4, 14),
            (5, 0),
            (5, 4),
            (5, 8),
            (5, 12),
            (6, 0),
            (6, 1),
            (6, 2),
            (6, 3),
            (6, 4),
            (6, 5),
            (6, 6),
            (6, 7),
            (6, 8),
            (6, 9),
            (6, 10),
            (6, 11),
            (6, 12),
            (6, 13),
            (6, 14),
            (7, 2),
            (7, 6),
            (7, 10),
            (7, 14),
            (8, 0),
            (8, 1),
            (8, 2),
            (8, 3),
            (8, 4),
            (8, 5),
            (8, 6),
            (8, 7),
            (8, 8),
            (8, 9),
            (8, 10),
            (8, 11),
            (8, 12),
            (8, 13),
            (8, 14),
            (9, 0),
            (9, 4),
            (9, 8),
            (9, 12),
            (10, 0),
            (10, 1),
            (10, 2),
            (10, 3),
            (10, 4),
            (10, 5),
            (10, 6),
            (10, 7),
            (10, 8),
            (10, 9),
            (10, 10),
            (10, 11),
            (10, 12),
            (10, 13),
            (10, 14),
            (11, 2),
            (11, 6),
            (11, 10),
            (11, 14),
            (12, 1),
            (12, 2),
            (12, 3),
            (12, 4),
            (12, 5),
            (12, 6),
            (12, 7),
            (12, 8),
            (12, 9),
            (12, 10),
            (12, 11),
            (12, 12),
            (12, 13),
            (12, 14),
        ]
        self.assertListEqual(_get_qubits_coordinates(127), exp)

    def test_error(self):
        r"""Test that an error is raised when the coordinates are unknown."""
        n = 10**6  # hopefully one day this test will fail
        with self.assertRaisesRegex(ValueError, f"Coordinates for {n}-qubit CPU are unknown."):
            _get_qubits_coordinates(n)
