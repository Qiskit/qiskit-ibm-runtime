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

"""Tests for EstimatorOptions class."""

from dataclasses import asdict
from unittest import skipUnless

from ddt import data, ddt, unpack
from pydantic import ValidationError
from qiskit.utils.optionals import HAS_AER

if HAS_AER:
    from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.options import EstimatorOptions, MeasureNoiseLearningOptions

from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend, get_primitive_inputs


@ddt
class TestEstimatorOptions(IBMTestCase):
    """Class for testing the EstimatorOptions class."""

    _shots_per_randomization_deprecation_msg = (
        "Specifying 'measure_noise_learning.shots_per_randomization' as an integer is deprecated"
    )

    @data(
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
            "'pec_mitigation' and 'zne_mitigation' options cannot be simultaneously enabled",
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

    @data(("auto", 0), (20, 1))
    @unpack
    def test_deprecate_measure_noise_learning_shots_per_randomization_on_nested_init(
        self, value, num_appearances
    ):
        """Integer shots_per_randomization warns when set via nested EstimatorOptions init."""
        with self.assertWarnsStrict(
            DeprecationWarning, self._shots_per_randomization_deprecation_msg, num_appearances
        ):
            options = EstimatorOptions(
                resilience={
                    "measure_mitigation": True,
                    "measure_noise_learning": {"shots_per_randomization": value},
                }
            )

        self.assertEqual(options.resilience.measure_noise_learning.shots_per_randomization, value)

    @data(("auto", 0), (20, 1))
    @unpack
    def test_deprecate_measure_noise_learning_shots_per_randomization_on_assignment(
        self, value, num_appearances
    ):
        """Integer shots_per_randomization warns on attribute assignment."""
        options = MeasureNoiseLearningOptions()

        with self.assertWarnsStrict(
            DeprecationWarning, self._shots_per_randomization_deprecation_msg, num_appearances
        ):
            options.shots_per_randomization = value

        self.assertEqual(options.shots_per_randomization, value)

    @data(("auto", 0), (20, 1))
    @unpack
    def test_deprecate_measure_noise_learning_shots_per_randomization_on_class_assignment(
        self, value, num_appearances
    ):
        """Integer shots_per_randomization warns when assigned on an estimator instance."""
        estimator = Estimator(mode=get_mocked_backend())

        with self.assertWarnsStrict(
            DeprecationWarning, self._shots_per_randomization_deprecation_msg, num_appearances
        ):
            estimator.options.resilience.measure_noise_learning.shots_per_randomization = value

        self.assertEqual(
            estimator.options.resilience.measure_noise_learning.shots_per_randomization, value
        )

    @data(("auto", 0), (20, 1))
    @unpack
    def test_deprecate_measure_noise_learning_shots_per_randomization_on_init(
        self, value, num_appearances
    ):
        """Auto shots_per_randomization does not warn on option init."""
        with self.assertWarnsStrict(
            DeprecationWarning, self._shots_per_randomization_deprecation_msg, num_appearances
        ):
            options = MeasureNoiseLearningOptions(shots_per_randomization=value)

        self.assertEqual(options.shots_per_randomization, value)

    def test_measure_noise_learning_shots_per_randomization_auto_on_assignment_does_not_warn(self):
        """Auto shots_per_randomization does not warn on attribute assignment."""
        options = MeasureNoiseLearningOptions()

        with self.assertWarnsStrict(
            DeprecationWarning, self._shots_per_randomization_deprecation_msg, 0
        ):
            options.shots_per_randomization = "auto"

        self.assertEqual(options.shots_per_randomization, "auto")

    @skipUnless(condition=HAS_AER, reason="qiskit-aer is required to run this test")
    def test_program_inputs(self):
        """Test converting to program inputs from estimator options."""
        noise_model = NoiseModel.from_backend(FakeManilaV2())
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
                "shots_per_randomization": "auto",
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
            resilience_level=resilience_level,
            seed_estimator=42,
            dynamical_decoupling=dynamical_decoupling,
            resilience=resilience,
            execution=execution,
            twirling=twirling,
            experimental={"foo": "bar", "execution": {"secret": 88}},
        )

        execution.update(
            {
                "secret": 88,
            }
        )
        options = {
            "default_precision": 0.5,
            "default_shots": 1000,
            "seed_estimator": 42,
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
        {"environment": {"log_level": "WARNING"}},
        {"execution": {"init_qubits": True}},
        {"twirling": {"enable_gates": True, "strategy": "active"}},
        {"environment": {"log_level": "ERROR"}},
        {"resilience": {"zne_mitigation": True, "zne": {"noise_factors": [1, 2, 3]}}},
    )
    def test_init_options_with_dictionary(self, opts_dict):
        """Test initializing options with dictionaries."""
        options = asdict(EstimatorOptions(**opts_dict))
        self.assertDictPartiallyEqual(options, opts_dict)

        # Make sure the structure didn't change.
        self.assertDictKeysEqual(asdict(EstimatorOptions()), options)

    @data(
        {"resilience_level": 2},
        {"max_execution_time": 200},
        {"resilience_level": 2},
        {"default_shots": 1024, "simulator": {"seed_simulator": 42}},
        {"resilience_level": 2, "default_shots": 2048},
        {
            "environment": {"log_level": "INFO"},
        },
        {"resilience": {"zne_mitigation": True, "zne": {"noise_factors": [1, 2, 3]}}},
    )
    def test_update_options(self, new_opts):
        """Test update method."""
        options = EstimatorOptions()
        options.update(**new_opts)

        # Make sure the values are equal.
        self.assertDictFlatPartiallyEqual(asdict(options), new_opts)
        # Make sure the structure didn't change.
        self.assertDictKeysEqual(asdict(options), asdict(EstimatorOptions()))

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
        estimator = Estimator(mode=backend, options=opt_dict)
        _ = estimator.run(**get_primitive_inputs(estimator))
        options = backend.service._run.call_args.kwargs["inputs"]["options"]
        self.assertDictEqual(options, opt_dict)

    def test_zero_resilience_level(self):
        """Test resilience_level=0."""
        opt_dict = {"resilience_level": 0}
        backend = get_mocked_backend()
        estimator = Estimator(mode=backend, options=opt_dict)
        _ = estimator.run(**get_primitive_inputs(estimator))
        options = backend.service._run.call_args.kwargs["inputs"]
        self.assertIn("resilience_level", options)
        self.assertEqual(options["resilience_level"], 0)
