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

import ddt
from qiskit.primitives.containers import DataBin, PubResult

from qiskit_ibm_runtime.debug_tools import NeatPubResult, NeatResult

from ...ibm_test_case import IBMTestCase
from ...utils import combine


def neat_pub_results():
    """Return a one-dimensional and a two-dimensional `NeatPubResult`."""
    return [NeatPubResult([1, 2, 3]), NeatPubResult([[1, 2], [3, 4]])]


def databins():
    """Return a one-dimensional and a two-dimensional `DataBin`."""
    return [DataBin(evs=[4, 5, 6]), DataBin(evs=[[5, 6], [7, 8]])]


def pub_results():
    """Return a `PubResult` for each of the databins."""
    return [PubResult(databin) for databin in databins()]


@ddt.ddt
class TestNeatPubResult(IBMTestCase):
    """Class for testing the NeatPubResult class."""

    @combine(
        scalar=[2, 4.5],
        idx=[0, 1],
        op_name=["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"],
    )
    def test_operations_with_scalarlike(self, scalar, idx, op_name):
        """Test operations between ``NeatPubResult`` and ``ScalarLike`` objects."""
        result = neat_pub_results()[idx]

        new_result = getattr(result, f"__{op_name}__")(scalar)
        new_vals = getattr(result.vals, f"__{op_name}__")(scalar)

        self.assertListEqual(new_result.vals.tolist(), new_vals.tolist())

    @combine(
        idx=[0, 1],
        op_name=["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"],
    )
    def test_operations_with_debugger_result(self, idx, op_name):
        """Test operations between two ``NeatPubResult`` objects."""
        result1 = neat_pub_results()[idx]
        result2 = 2 * result1

        new_result = getattr(result1, f"__{op_name}__")(result2)
        new_vals = getattr(result1.vals, f"__{op_name}__")(result2.vals)

        self.assertListEqual(new_result.vals.tolist(), new_vals.tolist())

    @combine(
        idx=[0, 1],
        op_name=["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"],
    )
    def test_operations_with_databins(self, idx, op_name):
        """Test operations between ``NeatPubResult`` and ``DataBin`` objects."""
        result = neat_pub_results()[idx]
        databin = databins()[idx]

        new_result = getattr(result, f"__{op_name}__")(databin)
        new_vals = getattr(result.vals, f"__{op_name}__")(databin.evs)

        self.assertListEqual(new_result.vals.tolist(), new_vals.tolist())

    @combine(op_name=["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"])
    def test_error_for_operations_with_databins(self, op_name):
        """Test the errors for operations between ``NeatPubResult`` and ``DataBin``."""
        result = neat_pub_results()[0]
        databin = DataBin(wrong_kwarg=result.vals)

        with self.assertRaisesRegex(ValueError, f"Cannot apply operator '__{op_name}__'"):
            getattr(result, f"__{op_name}__")(databin)

    @combine(
        idx=[0, 1],
        op_name=["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"],
    )
    def test_operations_with_pub_results(self, idx, op_name):
        """Test operations between ``NeatPubResult`` and ``PubResult`` objects."""
        result = neat_pub_results()[idx]
        pub_result = pub_results()[idx]

        new_result = getattr(result, f"__{op_name}__")(pub_result)
        new_vals = getattr(result.vals, f"__{op_name}__")(pub_result.data.evs)

        self.assertListEqual(new_result.vals.tolist(), new_vals.tolist())

    def test_abs(self):
        """Test the ``abs`` operator."""
        result = NeatPubResult([-1, 0, 1])
        new_result = abs(result)
        new_vals = abs(result.vals)

        self.assertListEqual(new_result.vals.tolist(), new_vals.tolist())

    @ddt.data(2, 4.5)
    def test_pow(self, p):
        """Test the ``pow`` operator."""
        result = neat_pub_results()[0]
        new_result = result**p
        new_vals = result.vals**p

        self.assertListEqual(new_result.vals.tolist(), new_vals.tolist())


@ddt.ddt
class TestNeatResult(IBMTestCase):
    """Class for testing the NeatResult class."""

    def test_getitem(self):
        """Test the ``__getitem__`` method of NeatResult."""
        results = neat_pub_results()
        r = NeatResult(results)

        self.assertListEqual(r[0].vals.tolist(), results[0].vals.tolist())
        self.assertListEqual(r[1].vals.tolist(), results[1].vals.tolist())

    def test_len(self):
        """Test the ``__len__`` method of NeatResult."""
        self.assertEqual(len(NeatResult(neat_pub_results())), 2)

    def test_iter(self):
        """Test the ``__iter__`` method of NeatResult."""
        results = neat_pub_results()
        for i, j in zip(NeatResult(results), results):
            self.assertListEqual(i.vals.tolist(), j.vals.tolist())
