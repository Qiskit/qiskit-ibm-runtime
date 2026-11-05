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
from typing import Any

import pytest
from pydantic import ValidationError
from qiskit.transpiler import CouplingMap

from qiskit_ibm_runtime.options import EstimatorOptions, SamplerOptions
from qiskit_ibm_runtime.runtime_options import RuntimeOptions


class TestOptionsV2:
    """Class for testing the v2 Options class."""

    @pytest.mark.parametrize("opt_cls", [EstimatorOptions, SamplerOptions])
    @pytest.mark.parametrize(
        "rt_options_kwargs",
        [
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
    def test_runtime_options(
        self, opt_cls: type[EstimatorOptions | SamplerOptions], rt_options_kwargs: dict[str, Any]
    ) -> None:
        """Test converting runtime options."""
        rt_options = RuntimeOptions(**rt_options_kwargs)
        assert vars(rt_options).items() >= opt_cls._get_runtime_options(vars(rt_options)).items()

    @pytest.mark.parametrize("opt_cls", [EstimatorOptions, SamplerOptions])
    def test_kwargs_options(self, opt_cls: type[EstimatorOptions | SamplerOptions]) -> None:
        """Test specifying arbitrary options."""
        with pytest.raises(ValidationError) as exc:
            _ = opt_cls(foo="foo")  # type: ignore[call-arg]
        assert "foo" in str(exc)

    @pytest.mark.parametrize("opt_cls", [EstimatorOptions, SamplerOptions])
    @pytest.mark.parametrize(
        "variant",
        [
            {(1, 0), (2, 1), (0, 1), (1, 2)},
            [[1, 0], [2, 1], [0, 1], [1, 2]],
            CouplingMap({(1, 0), (2, 1), (0, 1), (1, 2)}),
        ],
    )
    def test_coupling_map_options(
        self, opt_cls: type[EstimatorOptions | SamplerOptions], variant: set | list | CouplingMap
    ) -> None:
        """Check that coupling_map is processed correctly for various types."""
        options = opt_cls()
        options.simulator.coupling_map = variant  # type: ignore[union-attr]
        inputs = opt_cls._get_program_inputs(asdict(options))["options"]
        resulting_cmap = inputs["simulator"]["coupling_map"]
        assert {(1, 0), (2, 1), (0, 1), (1, 2)} == set(map(tuple, resulting_cmap))
