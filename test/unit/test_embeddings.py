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

"""Tests for the ``Embedding`` class."""

import textwrap

from qiskit_aer import AerSimulator

from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime.fake_provider import (
    FakeAlgiers,
    FakeAlmadenV2,
    FakeArmonkV2,
    FakeBrooklynV2,
    FakeCambridgeV2,
    FakeGuadalupeV2,
    FakeKyiv,
    FakeManilaV2,
    FakeMelbourneV2,
    FakeNighthawk,
    FakePerth,
    FakeRochesterV2,
    FakeMarrakesh,
    FakeTorino,
)
from qiskit_ibm_runtime.utils.embeddings import Embedding

from ..ibm_test_case import IBMTestCase


def ascii_to_coords(image: str, col_major: bool = False) -> list[tuple[int, int]]:
    """Parse an ASCII art image into a list of ``(row, col)`` coordinates.

    Every non-whitespace character is treated as a qubit. The row is the line index
    and the column is the character position, both after stripping common indentation
    and ignoring blank lines.

    Args:
        image: An ASCII art string where non-whitespace characters represent qubits.
        col_major: If ``True``, sort coordinates by column first, then row.

    Returns:
        List of integer coordinates.
    """
    lines = textwrap.dedent(image).splitlines()
    lines = [line for line in lines if line.strip()]
    coords = [
        (idx_row, idx_col)
        for idx_row, line in enumerate(lines)
        for idx_col, char in enumerate(line)
        if not char.isspace()
    ]
    if col_major:
        coords.sort(key=lambda p: (p[1], p[0]))
    return coords


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
        """Test the constructor from backend."""
        e = Embedding.from_backend(self.vigo)

        coo = [(1, 0), (0, 1), (1, 1), (1, 2), (2, 1)]
        self.assertEqual(e.coordinates, coo)
        self.assertEqual(e.coupling_map, self.vigo.coupling_map)

    def test_init_error(self):
        """Test the errors raised by the constructor."""
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


class TestCoordinates(IBMTestCase):
    """Class for testing the coordinates of backends."""

    def test_5(self):
        """Test for 5-qubit lattices."""
        embedding = Embedding.from_backend(FakeManilaV2())
        exp = [(1, 0), (0, 1), (1, 1), (1, 2), (2, 1)]
        self.assertListEqual(embedding.coordinates, exp)

    def test_7(self):
        """Test for 7-qubit lattices."""
        embedding = Embedding.from_backend(FakePerth())
        exp = ascii_to_coords(
            """
        xxx
         x
        xxx
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_15(self):
        """Test for 15-qubit lattices."""
        embedding = Embedding.from_backend(FakeMelbourneV2())
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
        self.assertListEqual(embedding.coordinates, exp)

    def test_16(self):
        """Test for 16-qubit lattices."""
        embedding = Embedding.from_backend(FakeGuadalupeV2())
        exp = ascii_to_coords(
            """
               x
            xxxxxxx
             x   x
             xxxxx
               x
            """,
            col_major=True,
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_20(self):
        """Test for 20-qubit lattices."""
        embedding = Embedding.from_backend(FakeAlmadenV2())
        exp = ascii_to_coords(
            """
        xxxxx
        xxxxx
        xxxxx
        xxxxx
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_27(self):
        """Test for 27-qubit lattices."""
        embedding = Embedding.from_backend(FakeAlgiers())
        exp = ascii_to_coords(
            """
               x   x
            xxxxxxxxxx
             x   x   x
             xxxxxxxxxx
               x   x
            """,
            col_major=True,
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_28(self):
        """Test for 28-qubit lattices."""
        embedding = Embedding.from_backend(FakeCambridgeV2())
        exp = ascii_to_coords(
            """
          xxxxx
          x   x
        xxxxxxxxx
        x   x   x
        xxxxxxxxx
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_53(self):
        """Test for 53-qubit lattices."""
        embedding = Embedding.from_backend(FakeRochesterV2())
        exp = ascii_to_coords(
            """
          xxxxx
          x   x
        xxxxxxxxx
        x   x   x
        xxxxxxxxx
          x   x
        xxxxxxxxx
        x   x   x
        xxxxxxxxx
          x   x
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_65(self):
        """Test for 65-qubit lattices."""
        embedding = Embedding.from_backend(FakeBrooklynV2())
        exp = ascii_to_coords(
            """
        xxxxxxxxxx
        x   x   x
        xxxxxxxxxxx
          x   x   x
        xxxxxxxxxxx
        x   x   x
        xxxxxxxxxxx
          x   x   x
         xxxxxxxxxx
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_120(self):
        """Test for 120-qubit lattices."""
        embedding = Embedding.from_backend(FakeNighthawk())
        exp = ascii_to_coords(
            """
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        xxxxxxxxxx
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_127(self):
        """Test for 127-qubit lattices."""
        embedding = Embedding.from_backend(FakeKyiv())
        exp = ascii_to_coords(
            """
        xxxxxxxxxxxxxx
        x   x   x   x
        xxxxxxxxxxxxxxx
          x   x   x   x
        xxxxxxxxxxxxxxx
        x   x   x   x
        xxxxxxxxxxxxxxx
          x   x   x   x
        xxxxxxxxxxxxxxx
        x   x   x   x
        xxxxxxxxxxxxxxx
          x   x   x   x
         xxxxxxxxxxxxxx
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_133(self):
        """Test for 133-qubit lattices."""
        embedding = Embedding.from_backend(FakeTorino())
        exp = ascii_to_coords(
            """
        xxxxxxxxxxxxxxx
        x   x   x   x
        xxxxxxxxxxxxxxx
          x   x   x   x
        xxxxxxxxxxxxxxx
        x   x   x   x
        xxxxxxxxxxxxxxx
          x   x   x   x
        xxxxxxxxxxxxxxx
        x   x   x   x
        xxxxxxxxxxxxxxx
          x   x   x   x
        xxxxxxxxxxxxxxx
        x   x   x   x
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_156(self):
        """Test for 156-qubit lattices."""
        embedding = Embedding.from_backend(FakeMarrakesh())
        exp = ascii_to_coords(
            """
        xxxxxxxxxxxxxxxx
           x   x   x   x
        xxxxxxxxxxxxxxxx
         x   x   x   x
        xxxxxxxxxxxxxxxx
           x   x   x   x
        xxxxxxxxxxxxxxxx
         x   x   x   x
        xxxxxxxxxxxxxxxx
           x   x   x   x
        xxxxxxxxxxxxxxxx
         x   x   x   x
        xxxxxxxxxxxxxxxx
           x   x   x   x
        xxxxxxxxxxxxxxxx
        """
        )
        self.assertListEqual(embedding.coordinates, exp)

    def test_error(self):
        """Test that an error is raised when the coordinates are unknown."""
        with self.assertRaisesRegex(ValueError, "Failed to fetch coordinates for backend"):
            Embedding.from_backend(FakeArmonkV2())
