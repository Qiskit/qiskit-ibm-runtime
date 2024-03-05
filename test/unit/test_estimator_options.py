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

"""Tests for EstimatorOptions class."""

from dataclasses import asdict

from ddt import data, ddt
from pydantic import ValidationError

from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.options import EstimatorOptions
from qiskit_ibm_runtime.fake_provider import FakeManila

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, dict_paritally_equal, flat_dict_partially_equal


@ddt
class TestEstimatorOptions(IBMTestCase):
    """Class for testing the EstimatorOptions class."""

    @data(
        {"optimization_level": 99},
        {"resilience_level": -1},
        {"default_precision": 0},
        {"dynamical_decoupling": "foo"},
        {"execution": {"init_qubits": 2}},
        {"twirling": {"strategy": "foo"}},
        {"resilience": {"zne": {"noise_factors": [0.5]}}},
        {"noise_factors": [1, 3, 5]},
        {"zne_mitigation": True, "pec_mitigation": True},
        {"simulator": {"noise_model": "foo"}},
        {"resilience": {"measure_noise_learning": {"num_randomizations": 1}}},
        {"resilience": {"zne": {"noise_factors": [1]}}},
    )
    def test_bad_inputs(self, val):
        """Test invalid inputs."""
        with self.assertRaises(ValidationError) as exc:
            EstimatorOptions(**val)
        self.assertIn(list(val.keys())[0], str(exc.exception))

    def test_program_inputs(self):
        """Test converting to program inputs from estimator options."""
        # pylint: disable=unexpected-keyword-arg

        noise_model = NoiseModel.from_backend(FakeManila())
        optimization_level = 0
        resilience_level = 2
        simulator = {
            "noise_model": noise_model,
            "seed_simulator": 42,
            "coupling_map": [[0, 1]],
            "basis_gates": ["u1"],
        }
        environment = {"log_level": "INFO"}
        dynamical_decoupling = {"enable": True, "sequence_type": "XX"}
        execution = {"init_qubits": True, "rep_delay": 0.01}
        resilience = {
            "measure_mitigation": True,
            "measure_noise_learning": {
                "num_randomizations": 1,
                "shots_per_randomization": 20,
            },
            "zne_mitigation": True,
            "zne": {"noise_factors": [1.0, 3.0], "extrapolator": "linear"},
            "pec_mitigation": False,
        }
        twirling = {"enable_gates": True, "enable_measure": True, "strategy": "all"}

        opt = EstimatorOptions(
            max_execution_time=100,
            environment=environment,
            simulator=simulator,
            default_precision=0.5,
            default_shots=1000,
            optimization_level=optimization_level,
            resilience_level=resilience_level,
            seed_estimator=42,
            dynamical_decoupling=dynamical_decoupling,
            resilience=resilience,
            execution=execution,
            twirling=twirling,
            experimental={"foo": "bar", "execution": {"secret": 88}},
        )

        transpilation = {
            "optimization_level": optimization_level,
        }
        execution.update(
            {
                "secret": 88,
            }
        )
        options = {
            "default_precision": 0.5,
            "default_shots": 1000,
            "seed_estimator": 42,
            "transpilation": transpilation,
            "twirling": twirling,
            "dynamical_decoupling": dynamical_decoupling,
            "execution": execution,
            "resilience": resilience,
            "experimental": {"foo": "bar"},
            "simulator": simulator,
        }
        expected = {
            "options": options,
            "resilience_level": resilience_level,
            "version": 2,
            "support_qiskit": True,
        }

        inputs = opt._get_program_inputs(asdict(opt))
        self.assertDictEqual(inputs, expected)

    @data(
        {},
        {"default_precision": 0.5},
        {"simulator": {"seed_simulator": 42}},
        {"optimization_level": 1, "environment": {"log_level": "WARNING"}},
        {"execution": {"init_qubits": True}},
        {"twirling": {"enable_gates": True, "strategy": "active"}},
        {"environment": {"log_level": "ERROR"}},
        {"resilience": {"zne_mitigation": True, "zne": {"noise_factors": [1, 2, 3]}}},
    )
    def test_init_options_with_dictionary(self, opts_dict):
        """Test initializing options with dictionaries."""
        options = asdict(EstimatorOptions(**opts_dict))
        self.assertTrue(
            dict_paritally_equal(options, opts_dict),
            f"options={options}, opts_dict={opts_dict}",
        )

        # Make sure the structure didn't change.
        self.assertTrue(dict_keys_equal(asdict(EstimatorOptions()), options), f"options={options}")

    @data(
        {"resilience_level": 2},
        {"max_execution_time": 200},
        {"resilience_level": 2, "optimization_level": 1},
        {"default_shots": 1024, "seed_simulator": 42},
        {"resilience_level": 2, "default_shots": 2048},
        {
            "optimization_level": 1,
            "log_level": "INFO",
        },
        {"zne_mitigation": True, "noise_factors": [1, 2, 3]},
    )
    def test_update_options(self, new_opts):
        """Test update method."""
        options = EstimatorOptions()
        options.update(**new_opts)

        # Make sure the values are equal.
        self.assertTrue(
            flat_dict_partially_equal(asdict(options), new_opts),
            f"new_opts={new_opts}, combined={options}",
        )
        # Make sure the structure didn't change.
        self.assertTrue(dict_keys_equal(asdict(options), asdict(EstimatorOptions())))
