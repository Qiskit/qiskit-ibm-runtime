# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
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

from ddt import data, ddt
from pydantic import ValidationError

from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.options import SamplerOptions
from qiskit_ibm_runtime.fake_provider import FakeManila

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, dict_paritally_equal, flat_dict_partially_equal


@ddt
class TestSamplerOptions(IBMTestCase):
    """Class for testing the SamplerOptions class."""

    @data(
        {"optimization_level": 1},
        {"default_shots": 0.1},
        {"dynamical_decoupling": {"sequence_type": "foo"}},
        {"execution": {"init_qubits": 2}},
    )
    def test_bad_inputs(self, val):
        """Test invalid inputs."""
        with self.assertRaises(ValidationError) as exc:
            SamplerOptions(**val)
        self.assertIn(list(val.keys())[0], str(exc.exception))

    def test_program_inputs(self):
        """Test converting to program inputs from estimator options."""
        # pylint: disable=unexpected-keyword-arg

        noise_model = NoiseModel.from_backend(FakeManila())
        simulator = {
            "noise_model": noise_model,
            "seed_simulator": 42,
            "coupling_map": [[0, 1]],
            "basis_gates": ["u1"],
        }
        environment = {"log_level": "INFO"}
        dynamical_decoupling = {"enable": True, "sequence_type": "XX"}
        execution = {"init_qubits": True, "rep_delay": 0.01}

        opt = SamplerOptions(
            max_execution_time=100,
            environment=environment,
            simulator=simulator,
            default_shots=1000,
            dynamical_decoupling=dynamical_decoupling,
            execution=execution,
            experimental={"foo": "bar", "execution": {"secret": 88}},
        )
        execution.update(
            {
                "secret": 88,
            }
        )
        options = {
            "default_shots": 1000,
            "dynamical_decoupling": dynamical_decoupling,
            "execution": execution,
            "experimental": {"foo": "bar"},
            "simulator": simulator,
        }
        expected = {"options": options, "version": 2, "support_qiskit": True}

        inputs = opt._get_program_inputs(asdict(opt))
        self.assertDictEqual(inputs, expected)

    @data(
        {},
        {"default_shots": 1000},
        {"simulator": {"seed_simulator": 42}},
        {"default_shots": 1, "environment": {"log_level": "WARNING"}},
        {"execution": {"init_qubits": True}},
        {"dynamical_decoupling": {"enable": True, "sequence_type": "XX"}},
        {"environment": {"log_level": "ERROR"}},
    )
    def test_init_options_with_dictionary(self, opts_dict):
        """Test initializing options with dictionaries."""
        options = asdict(SamplerOptions(**opts_dict))
        self.assertTrue(
            dict_paritally_equal(options, opts_dict),
            f"options={options}, opts_dict={opts_dict}",
        )

        # Make sure the structure didn't change.
        self.assertTrue(dict_keys_equal(asdict(SamplerOptions()), options), f"options={options}")

    @data(
        {"default_shots": 4000},
        {"max_execution_time": 200},
        {"default_shots": 1024, "seed_simulator": 42},
        {
            "sequence_type": "XX",
            "log_level": "INFO",
        },
    )
    def test_update_options(self, new_opts):
        """Test update method."""
        options = SamplerOptions()
        options.update(**new_opts)

        # Make sure the values are equal.
        self.assertTrue(
            flat_dict_partially_equal(asdict(options), new_opts),
            f"new_opts={new_opts}, combined={options}",
        )
        # Make sure the structure didn't change.
        self.assertTrue(dict_keys_equal(asdict(options), asdict(SamplerOptions())))
