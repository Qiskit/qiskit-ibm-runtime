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

"""Tests for result classes for Neat objects."""

import pytest
from qiskit.primitives.containers import DataBin, PubResult

from qiskit_ibm_runtime.debug_tools import NeatPubResult, NeatResult


def neat_pub_results() -> list[NeatPubResult]:
    """Return a one-dimensional and a two-dimensional `NeatPubResult`."""
    return [NeatPubResult([1, 2, 3]), NeatPubResult([[1, 2], [3, 4]])]


def databins() -> list[DataBin]:
    """Return a one-dimensional and a two-dimensional `DataBin`."""
    return [DataBin(evs=[4, 5, 6]), DataBin(evs=[[5, 6], [7, 8]])]


def pub_results() -> list[PubResult]:
    """Return a `PubResult` for each of the databins."""
    return [PubResult(databin) for databin in databins()]


class TestNeatPubResult:
    """Class for testing the NeatPubResult class."""

    @pytest.mark.parametrize("scalar", [2, 4.5])
    @pytest.mark.parametrize("idx", [0, 1])
    @pytest.mark.parametrize(
        "op_name", ["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"]
    )
    def test_operations_with_scalarlike(self, scalar: float, idx: int, op_name: str) -> None:
        """Test operations between ``NeatPubResult`` and ``ScalarLike`` objects."""
        result = neat_pub_results()[idx]

        new_result = getattr(result, f"__{op_name}__")(scalar)
        new_vals = getattr(result.vals, f"__{op_name}__")(scalar)

        assert new_result.vals.tolist() == new_vals.tolist()

    @pytest.mark.parametrize("idx", [0, 1])
    @pytest.mark.parametrize(
        "op_name", ["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"]
    )
    def test_operations_with_debugger_result(self, idx: int, op_name: str) -> None:
        """Test operations between two ``NeatPubResult`` objects."""
        result1 = neat_pub_results()[idx]
        result2 = 2 * result1

        new_result = getattr(result1, f"__{op_name}__")(result2)
        new_vals = getattr(result1.vals, f"__{op_name}__")(result2.vals)

        assert new_result.vals.tolist() == new_vals.tolist()

    @pytest.mark.parametrize("idx", [0, 1])
    @pytest.mark.parametrize(
        "op_name", ["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"]
    )
    def test_operations_with_databins(self, idx: int, op_name: str) -> None:
        """Test operations between ``NeatPubResult`` and ``DataBin`` objects."""
        result = neat_pub_results()[idx]
        databin = databins()[idx]

        new_result = getattr(result, f"__{op_name}__")(databin)
        new_vals = getattr(result.vals, f"__{op_name}__")(databin.evs)

        assert new_result.vals.tolist() == new_vals.tolist()

    @pytest.mark.parametrize(
        "op_name", ["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"]
    )
    def test_error_for_operations_with_databins(self, op_name: str) -> None:
        """Test the errors for operations between ``NeatPubResult`` and ``DataBin``."""
        result = neat_pub_results()[0]
        databin = DataBin(wrong_kwarg=result.vals)

        with pytest.raises(ValueError, match=f"Cannot apply operator '__{op_name}__'"):
            getattr(result, f"__{op_name}__")(databin)

    @pytest.mark.parametrize("idx", [0, 1])
    @pytest.mark.parametrize(
        "op_name", ["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"]
    )
    def test_operations_with_pub_results(self, idx: int, op_name: str) -> None:
        """Test operations between ``NeatPubResult`` and ``PubResult`` objects."""
        result = neat_pub_results()[idx]
        pub_result = pub_results()[idx]

        new_result = getattr(result, f"__{op_name}__")(pub_result)
        new_vals = getattr(result.vals, f"__{op_name}__")(pub_result.data.evs)

        assert new_result.vals.tolist() == new_vals.tolist()

    def test_abs(self) -> None:
        """Test the ``abs`` operator."""
        result = NeatPubResult([-1, 0, 1])
        new_result = abs(result)
        new_vals = abs(result.vals)

        assert new_result.vals.tolist() == new_vals.tolist()

    @pytest.mark.parametrize("p", [2, 4.5])
    def test_pow(self, p: float) -> None:
        """Test the ``pow`` operator."""
        result = neat_pub_results()[0]
        new_result = result**p
        new_vals = result.vals**p

        assert new_result.vals.tolist() == new_vals.tolist()


class TestNeatResult:
    """Class for testing the NeatResult class."""

    def test_getitem(self) -> None:
        """Test the ``__getitem__`` method of NeatResult."""
        results = neat_pub_results()
        r = NeatResult(results)

        assert r[0].vals.tolist() == results[0].vals.tolist()
        assert r[1].vals.tolist() == results[1].vals.tolist()

    def test_len(self) -> None:
        """Test the ``__len__`` method of NeatResult."""
        assert len(NeatResult(neat_pub_results())) == 2

    def test_iter(self) -> None:
        """Test the ``__iter__`` method of NeatResult."""
        results = neat_pub_results()
        for i, j in zip(NeatResult(results), results):  # type: ignore[call-overload]
            assert i.vals.tolist() == j.vals.tolist()
