# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Options class."""

from dataclasses import asdict

from ddt import data, ddt
from pydantic import ValidationError
from qiskit.transpiler import CouplingMap

from qiskit_ibm_runtime.options import EstimatorOptions, SamplerOptions
from qiskit_ibm_runtime.runtime_options import RuntimeOptions

from ...ibm_test_case import IBMTestCase
from ...utils import combine


@ddt
class TestOptionsV2(IBMTestCase):
    """Class for testing the v2 Options class."""

    @combine(
        opt_cls=[EstimatorOptions, SamplerOptions],
        rt_options_kwargs=[
            {
                "backend": "ibm_gotham",
                "image": "foo:bar",
                "log_level": "DEBUG",
                "instance": "crn",
                "job_tags": ["foo", "bar"],
                "max_execution_time": 600,
            },
            {"backend": "foo", "log_level": "DEBUG"},
        ],
    )
    def test_runtime_options(self, opt_cls, rt_options_kwargs):
        """Test converting runtime options."""
        rt_options = RuntimeOptions(**rt_options_kwargs)
        assert vars(rt_options).items() >= opt_cls._get_runtime_options(vars(rt_options)).items()

    @data(EstimatorOptions, SamplerOptions)
    def test_kwargs_options(self, opt_cls):
        """Test specifying arbitrary options."""
        with self.assertRaises(ValidationError) as exc:
            _ = opt_cls(foo="foo")
        assert "foo" in str(exc.exception)

    @combine(
        opt_cls=[EstimatorOptions, SamplerOptions],
        variant=[
            {(1, 0), (2, 1), (0, 1), (1, 2)},
            [[1, 0], [2, 1], [0, 1], [1, 2]],
            CouplingMap({(1, 0), (2, 1), (0, 1), (1, 2)}),
        ],
    )
    def test_coupling_map_options(self, opt_cls, variant):
        """Check that coupling_map is processed correctly for various types."""
        options = opt_cls()
        options.simulator.coupling_map = variant
        inputs = opt_cls._get_program_inputs(asdict(options))["options"]
        resulting_cmap = inputs["simulator"]["coupling_map"]
        assert {(1, 0), (2, 1), (0, 1), (1, 2)} == set(map(tuple, resulting_cmap))
