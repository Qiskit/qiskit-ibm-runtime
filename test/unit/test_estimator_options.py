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
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime.options import EstimatorOptions
from qiskit_ibm_runtime.fake_provider import FakeManila

from ..ibm_test_case import IBMTestCase
from ..utils import (
    dict_keys_equal,
    dict_paritally_equal,
    flat_dict_partially_equal,
    get_mocked_backend,
    get_primitive_inputs,
)


@ddt
class TestEstimatorOptions(IBMTestCase):
    """Class for testing the EstimatorOptions class."""

    @data(
        ({"optimization_level": 99}, "optimization_level must be <=1"),
        ({"resilience_level": -1}, "resilience_level must be >=0"),
        ({"default_precision": 0}, "default_precision must be >0"),
        (
            {"dynamical_decoupling": "foo"},
            "Input should be a dictionary or an instance of DynamicalDecouplingOptions",
        ),
        ({"execution": {"init_qubits": 2}}, "Input should be a valid boolean"),
        (
            {"twirling": {"strategy": "foo"}},
            "Input should be 'active', 'active-accum', 'active-circuit' or 'all'",
        ),
        (
            {"resilience": {"zne": {"noise_factors": [0.5]}}},
            "noise_factors` option value must all be >= 1",
        ),
        ({"noise_factors": [1, 3, 5]}, "Unexpected keyword argument"),
        (
            {"resilience": {"zne_mitigation": True, "pec_mitigation": True}},
            "pec_mitigation and zne_mitigation`options cannot be simultaneously enabled",
        ),
        (
            {"simulator": {"noise_model": "foo"}},
            "'noise_model' can only be a dictionary or qiskit_aer.noise.NoiseModel",
        ),
        (
            {"resilience": {"measure_noise_learning": {"num_randomizations": 1}}},
            "'measure_noise_learning' options are set, but 'measure_mitigation' is not set to True",
        ),
        (
            {
                "resilience": {
                    "measure_mitigation": True,
                    "measure_noise_learning": {"num_randomizations": 0},
                }
            },
            "num_randomizations must be >=1",
        ),
        (
            {"resilience": {"zne_mitigation": True, "zne": {"noise_factors": [1]}}},
            "exponential requires at least 2 noise_factors",
        ),
        (
            {"resilience": {"zne_mitigation": True, "zne": {"noise_factors": []}}},
            "exponential requires at least 2 noise_factors",
        ),
        (
            {"resilience": {"zne_mitigation": True, "zne": {"amplifier": "not_accepted"}}},
            "Input should be 'gate_folding', 'gate_folding_front', 'gate_folding_back' or 'pea'",
        ),
    )
    def test_bad_inputs(self, val):
        """Test invalid inputs."""
        bad_input, error_msg = val
        with self.assertRaisesRegex(ValidationError, error_msg):
            EstimatorOptions(**bad_input)

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
            "zne": {
                "noise_factors": [1.0, 3.0],
                "extrapolator": "linear",
                "amplifier": "gate_folding",
            },
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
        {"default_shots": 1024, "simulator": {"seed_simulator": 42}},
        {"resilience_level": 2, "default_shots": 2048},
        {
            "optimization_level": 1,
            "environment": {"log_level": "INFO"},
        },
        {"resilience": {"zne_mitigation": True, "zne": {"noise_factors": [1, 2, 3]}}},
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

    @data(
        {"default_shots": 0},
        {"seed_estimator": 0},
        {"resilience": {"layer_noise_learning": {"max_layers_to_learn": 0}}},
        {"resilience": {"layer_noise_learning": {"layer_pair_depths": [0]}}},
        {"execution": {"rep_delay": 0.0}},
    )
    def test_zero_values(self, opt_dict):
        """Test options with values of 0."""
        backend = get_mocked_backend()
        estimator = Estimator(backend=backend, options=opt_dict)
        _ = estimator.run(**get_primitive_inputs(estimator))
        options = backend.service.run.call_args.kwargs["inputs"]["options"]
        self.assertDictEqual(options, opt_dict)

    def test_zero_optimization_level(self):
        """Test optimization_level=0."""
        opt_dict = {"optimization_level": 0}
        backend = get_mocked_backend()
        estimator = Estimator(backend=backend, options=opt_dict)
        _ = estimator.run(**get_primitive_inputs(estimator))
        options = backend.service.run.call_args.kwargs["inputs"]["options"]
        self.assertDictEqual(options, {"transpilation": {"optimization_level": 0}})

    def test_zero_resilience_level(self):
        """Test resilience_level=0"""
        opt_dict = {"resilience_level": 0}
        backend = get_mocked_backend()
        estimator = Estimator(backend=backend, options=opt_dict)
        _ = estimator.run(**get_primitive_inputs(estimator))
        options = backend.service.run.call_args.kwargs["inputs"]
        self.assertIn("resilience_level", options)
        self.assertEqual(options["resilience_level"], 0)

    def test_optimization_level_deprecation(self):
        """Test optimization level being deprecated."""
        backend = get_mocked_backend()
        estimator = Estimator(backend=backend, options={"optimization_level": 1})
        with self.assertWarnsRegex(DeprecationWarning, r".*optimization_level.*"):
            _ = estimator.run(**get_primitive_inputs(estimator))
