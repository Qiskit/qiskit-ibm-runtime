# This code is part of Qiskit.
#
# (C) Copyright IBM 2023-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for SamplerOptions class."""

from dataclasses import asdict
from typing import Any

import pytest
from pydantic import ValidationError
from qiskit.utils.optionals import HAS_AER

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.options import SamplerOptions

from ...asserts import (
    assert_dict_flat_partially_equal,
    assert_dict_keys_equal,
    assert_dict_partially_equal,
)
from ...utils import get_mocked_backend, get_primitive_inputs

if HAS_AER:
    from qiskit_aer.noise import NoiseModel


class TestSamplerOptions:
    """Class for testing the SamplerOptions class."""

    @pytest.mark.parametrize(
        "val",
        [
            {"optimization_level": 1},
            {"default_shots": 0.1},
            {"dynamical_decoupling": {"sequence_type": "foo"}},
            {"execution": {"init_qubits": 2}},
        ],
    )
    def test_bad_inputs(self, val: dict[str, Any]) -> None:
        """Test invalid inputs."""
        with pytest.raises(ValidationError) as exc:
            SamplerOptions(**val)
        assert list(val.keys())[0] in str(exc)

    @pytest.mark.skipif(not HAS_AER, reason="qiskit-aer is required to run this test")
    def test_program_inputs(self) -> None:
        """Test converting to program inputs from sampler options."""
        noise_model = NoiseModel()
        simulator = {
            "noise_model": noise_model,
            "seed_simulator": 42,
            "coupling_map": [[0, 1]],
            "basis_gates": ["u1"],
        }
        environment = {"log_level": "INFO"}
        dynamical_decoupling = {"enable": True, "sequence_type": "XX"}
        execution = {"init_qubits": True, "rep_delay": 0.01}
        twirling = {"enable_gates": True, "enable_measure": True, "strategy": "active-circuit"}

        opt = SamplerOptions(
            max_execution_time=100,
            environment=environment,
            simulator=simulator,
            default_shots=1000,
            dynamical_decoupling=dynamical_decoupling,
            twirling=twirling,
            execution=execution,
            experimental={"foo": "bar", "execution": {"secret": 88}},
        )  # type: ignore[call-arg]
        execution.update(
            {
                "secret": 88,
            }
        )
        options = {
            "default_shots": 1000,
            "dynamical_decoupling": dynamical_decoupling,
            "twirling": {
                "enable_gates": True,
                "enable_measure": True,
                "strategy": "active-circuit",
            },
            "execution": execution,
            "experimental": {"foo": "bar"},
            "simulator": simulator,
        }
        expected = {"options": options, "version": 2, "support_qiskit": True}

        inputs = opt._get_program_inputs(asdict(opt))
        assert inputs == expected

    @pytest.mark.parametrize(
        "opts_dict",
        [
            {},
            {"default_shots": 1000},
            {"simulator": {"seed_simulator": 42}},
            {"default_shots": 1, "environment": {"log_level": "WARNING"}},
            {"execution": {"init_qubits": True, "meas_type": "avg_kerneled"}},
            {"dynamical_decoupling": {"enable": True, "sequence_type": "XX"}},
            {"environment": {"log_level": "ERROR"}},
            {"twirling": {"enable_gates": True, "strategy": "active"}},
        ],
    )
    def test_init_options_with_dictionary(self, opts_dict: dict[str, Any]) -> None:
        """Test initializing options with dictionaries."""
        options = asdict(SamplerOptions(**opts_dict))
        assert_dict_partially_equal(options, opts_dict)
        # Make sure the structure didn't change.
        assert_dict_keys_equal(asdict(SamplerOptions()), options)

    @pytest.mark.parametrize(
        "new_opts",
        [
            {"default_shots": 4000},
            {"max_execution_time": 200},
            {"default_shots": 1024, "simulator": {"seed_simulator": 42}},
            {
                "dynamical_decoupling": {"sequence_type": "XX"},
                "environment": {"log_level": "INFO"},
            },
            {"twirling": {"enable_gates": True, "strategy": "active"}},
        ],
    )
    def test_update_options(self, new_opts: dict[str, Any]) -> None:
        """Test update method."""
        options = SamplerOptions()
        options.update(**new_opts)

        # Make sure the values are equal.
        assert_dict_flat_partially_equal(asdict(options), new_opts)
        # Make sure the structure didn't change.
        assert_dict_keys_equal(asdict(options), asdict(SamplerOptions()))

    @pytest.mark.parametrize(
        "opt_dict",
        [
            {"default_shots": 0},
            {"execution": {"rep_delay": 0.0}},
        ],
    )
    def test_zero_values(self, opt_dict: dict[str, Any]) -> None:
        """Test options with values of 0."""
        backend = get_mocked_backend()
        sampler = Sampler(mode=backend, options=opt_dict)
        _ = sampler.run(**get_primitive_inputs(sampler))
        options = backend.service._run.call_args.kwargs["inputs"]["options"]  # type: ignore[attr-defined]
        assert options == opt_dict
