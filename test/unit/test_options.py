# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
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
from qiskit.providers import BackendV1
from qiskit.providers.fake_provider import FakeManila, FakeNairobiV2
from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime import Options, RuntimeOptions
from qiskit_ibm_runtime.options.utils import merge_options
from qiskit_ibm_runtime.options import EstimatorOptions, SamplerOptions
from qiskit_ibm_runtime.utils.qctrl import _warn_and_clean_options

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, dict_paritally_equal, flat_dict_partially_equal, combine


@ddt
class TestOptions(IBMTestCase):
    """Class for testing the Options class."""

    def test_merge_options(self):
        """Test merging options."""
        options_vars = [
            {},
            {"resilience_level": 9},
            {"resilience_level": 8, "transpilation": {"initial_layout": [1, 2]}},
            {"shots": 99, "seed_simulator": 42},
            {"resilience_level": 99, "shots": 98, "initial_layout": [3, 4]},
            {
                "initial_layout": [1, 2],
                "transpilation": {"layout_method": "trivial"},
                "log_level": "INFO",
            },
        ]
        for new_ops in options_vars:
            with self.subTest(new_ops=new_ops):
                options = Options()
                combined = merge_options(asdict(options), new_ops)

                # Make sure the values are equal.
                self.assertTrue(
                    flat_dict_partially_equal(combined, new_ops),
                    f"new_ops={new_ops}, combined={combined}",
                )
                # Make sure the structure didn't change.
                self.assertTrue(
                    dict_keys_equal(combined, asdict(options)),
                    f"options={options}, combined={combined}",
                )

    def test_runtime_options(self):
        """Test converting runtime options."""
        full_options = RuntimeOptions(
            backend="ibm_gotham",
            image="foo:bar",
            log_level="DEBUG",
            instance="h/g/p",
            job_tags=["foo", "bar"],
            max_execution_time=600,
        )
        partial_options = RuntimeOptions(backend="foo", log_level="DEBUG")

        for rt_options in [full_options, partial_options]:
            with self.subTest(rt_options=rt_options):
                self.assertGreaterEqual(
                    vars(rt_options).items(),
                    Options._get_runtime_options(vars(rt_options)).items(),
                )

    def test_program_inputs(self):
        """Test converting to program inputs."""
        noise_model = NoiseModel.from_backend(FakeNairobiV2())
        options = Options(  # pylint: disable=unexpected-keyword-arg
            optimization_level=1,
            resilience_level=2,
            transpilation={"initial_layout": [1, 2], "skip_transpilation": True},
            execution={"shots": 100},
            environment={"log_level": "DEBUG"},
            simulator={"noise_model": noise_model},
            resilience={"noise_factors": (1, 2, 4)},
        )
        inputs = Options._get_program_inputs(asdict(options))

        expected = {
            "run_options": {"shots": 100, "noise_model": noise_model},
            "transpilation_settings": {
                "optimization_settings": {"level": 1},
                "skip_transpilation": True,
                "initial_layout": [1, 2],
            },
            "resilience_settings": {
                "level": 2,
                "noise_factors": (1, 2, 4),
            },
        }
        self.assertTrue(
            dict_paritally_equal(inputs, expected),
            f"inputs={inputs}, expected={expected}",
        )

    def test_init_options_with_dictionary(self):
        """Test initializing options with dictionaries."""

        options_dicts = [
            {},
            {"resilience_level": 9},
            {"simulator": {"seed_simulator": 42}},
            {"resilience_level": 8, "environment": {"log_level": "WARNING"}},
            {
                "transpilation": {"initial_layout": [1, 2], "layout_method": "trivial"},
                "execution": {"shots": 100},
            },
            {"resilience": {"noise_factors": (0, 2, 4)}},
            {"environment": {"log_level": "ERROR"}},
        ]

        for opts_dict in options_dicts:
            with self.subTest(opts_dict=opts_dict):
                options = asdict(Options(**opts_dict))
                self.assertTrue(
                    dict_paritally_equal(options, opts_dict),
                    f"options={options}, opts_dict={opts_dict}",
                )

                # Make sure the structure didn't change.
                self.assertTrue(dict_keys_equal(asdict(Options()), options), f"options={options}")

    def test_kwargs_options(self):
        """Test specifying arbitrary options."""
        with self.assertRaises(TypeError) as exc:
            _ = Options(foo="foo")  # pylint: disable=unexpected-keyword-arg
        self.assertIn(
            "__init__() got an unexpected keyword argument 'foo'",
            str(exc.exception),
        )

    def test_unsupported_options(self):
        """Test error on unsupported second level options"""
        # defining minimal dict of options
        options = {
            "optimization_level": 1,
            "resilience_level": 2,
            "transpilation": {"initial_layout": [1, 2], "skip_transpilation": True},
            "execution": {"shots": 100},
            "environment": {"log_level": "DEBUG"},
            "resilience": {
                "noise_factors": (0, 2, 4),
                "extrapolator": "LinearExtrapolator",
            },
        }
        Options.validate_options(options)
        for opt in ["resilience", "simulator", "transpilation", "execution"]:
            temp_options = options.copy()
            temp_options[opt] = {"aaa": "bbb"}
            with self.assertRaises(ValidationError) as exc:
                Options.validate_options(temp_options)
            self.assertIn("bbb", str(exc.exception))

    def test_coupling_map_options(self):
        """Check that coupling_map is processed correctly for various types"""
        coupling_map = {(1, 0), (2, 1), (0, 1), (1, 2)}
        coupling_maps = [
            coupling_map,
            list(map(list, coupling_map)),
            CouplingMap(coupling_map),
        ]
        for variant in coupling_maps:
            with self.subTest(opts_dict=variant):
                options = Options()
                options.simulator.coupling_map = variant
                inputs = Options._get_program_inputs(asdict(options))
                resulting_cmap = inputs["transpilation_settings"]["coupling_map"]
                self.assertEqual(coupling_map, set(map(tuple, resulting_cmap)))

    @data(FakeManila(), FakeNairobiV2())
    def test_simulator_set_backend(self, fake_backend):
        """Test Options.simulator.set_backend method."""

        options = Options()
        options.simulator.seed_simulator = 42
        options.simulator.set_backend(fake_backend)

        noise_model = NoiseModel.from_backend(fake_backend)
        basis_gates = (
            fake_backend.configuration().basis_gates
            if isinstance(fake_backend, BackendV1)
            else fake_backend.operation_names
        )
        coupling_map = (
            fake_backend.configuration().coupling_map
            if isinstance(fake_backend, BackendV1)
            else fake_backend.coupling_map
        )

        expected_options = Options()
        expected_options.simulator = {
            "noise_model": noise_model,
            "basis_gates": basis_gates,
            "coupling_map": coupling_map,
            "seed_simulator": 42,
        }
        self.assertDictEqual(asdict(options), asdict(expected_options))

    def test_qctrl_overrides(self):
        """Test override of options"""
        all_test_options = [
            (
                {
                    "optimization_level": 2,
                    "transpilation": {"approximation_degree": 1},
                    "resilience_level": 3,
                    "resilience": {
                        "noise_factors": (1, 3, 5),
                        "extrapolator": "Linear",
                    },
                },
                {
                    "optimization_level": 3,
                    "transpilation": {"approximation_degree": 0},
                    "resilience_level": 1,
                    "resilience": {
                        "noise_factors": None,
                        "extrapolator": None,
                    },
                },
            ),
            (
                {
                    "optimization_level": 0,
                    "transpilation": {"approximation_degree": 1, "skip_transpilation": True},
                    "resilience_level": 1,
                },
                {
                    "optimization_level": 3,
                    "transpilation": {"approximation_degree": 0, "skip_transpilation": False},
                    "resilience_level": 1,
                },
            ),
            (
                {
                    "optimization_level": 0,
                    "transpilation": {"skip_transpilation": True},
                    "resilience_level": 1,
                },
                {
                    "optimization_level": 3,
                    "transpilation": {"skip_transpilation": False},
                    "resilience_level": 1,
                },
            ),
        ]
        for option, expected_ in all_test_options:
            with self.subTest(msg=f"{option}"):
                _warn_and_clean_options(option)
                self.assertEqual(expected_, option)


@ddt
class TestOptionsV2(IBMTestCase):
    """Class for testing the v2 Options class."""

    def test_merge_options(self):
        """Test merging options."""
        options_vars = [
            {},
            {"resilience_level": 9},
            {"shots": 99, "seed_simulator": 42},
            {"resilience_level": 99, "shots": 98, "skip_transpilation": True},
            {
                "transpilation": {"optimization_level": 1},
                "log_level": "INFO",
            },
        ]
        for new_ops in options_vars:
            with self.subTest(new_ops=new_ops):
                options = EstimatorOptions()
                combined = merge_options(asdict(options), new_ops)

                # Make sure the values are equal.
                self.assertTrue(
                    flat_dict_partially_equal(combined, new_ops),
                    f"new_ops={new_ops}, combined={combined}",
                )
                # Make sure the structure didn't change.
                self.assertTrue(
                    dict_keys_equal(combined, asdict(options)),
                    f"options={options}, combined={combined}",
                )

    @data(EstimatorOptions, SamplerOptions)
    def test_runtime_options(self, opt_cls):
        """Test converting runtime options."""
        full_options = RuntimeOptions(
            backend="ibm_gotham",
            image="foo:bar",
            log_level="DEBUG",
            instance="h/g/p",
            job_tags=["foo", "bar"],
            max_execution_time=600,
        )
        partial_options = RuntimeOptions(backend="foo", log_level="DEBUG")

        for rt_options in [full_options, partial_options]:
            with self.subTest(rt_options=rt_options):
                self.assertGreaterEqual(
                    vars(rt_options).items(),
                    opt_cls._get_runtime_options(vars(rt_options)).items(),
                )

    @data(EstimatorOptions, SamplerOptions)
    def test_program_inputs(self, opt_cls):
        """Test converting to program inputs from v2 options."""

        noise_model = NoiseModel.from_backend(FakeManila())
        optimization_level = 0
        transpilation = {
            "skip_transpilation": False,
            "optimization_level": optimization_level,
        }
        simulator = {
            "noise_model": noise_model,
            "seed_simulator": 42,
            "coupling_map": [[0, 1]],
            "basis_gates": ["u1"],
        }
        execution = {
            "shots": 400,
            "init_qubits": True,
            "samples": 20,
            "shots_per_sample": 20,
            "interleave_samples": True,
        }

        twirling = {"gates": True, "measure": True, "strategy": "all"}
        resilience = {
            "measure_noise_mitigation": True,
            "zne_mitigation": True,
            "zne_noise_factors": [1, 3],
            "zne_extrapolator": "exponential",
            "zne_stderr_threshold": 1,
            "pec_mitigation": False,
            "pec_max_overhead": 2,
        }

        estimator_extra = {}
        if isinstance(opt_cls, EstimatorOptions):
            estimator_extra = {
                "resilience_level": 2,
                "resilience": resilience,
                "seed_estimator": 42,
            }

        opt = opt_cls(
            max_execution_time=100,
            simulator=simulator,
            dynamical_decoupling="XX",
            transpilation=transpilation,
            execution=execution,
            twirling=twirling,
            experimental={"foo": "bar"},
            **estimator_extra,
        )

        transpilation.pop("skip_transpilation")
        transpilation.update(
            {
                "coupling_map": simulator.pop("coupling_map"),
                "basis_gates": simulator.pop("basis_gates"),
            }
        )
        execution.update(
            {
                "noise_model": simulator.pop("noise_model"),
                "seed_simulator": simulator.pop("seed_simulator"),
            }
        )
        expected = {
            "transpilation": transpilation,
            "skip_transpilation": False,
            "twirling": twirling,
            "dynamical_decoupling": "XX",
            "execution": execution,
            "foo": "bar",
            "version": 2,
            **estimator_extra,
        }

        inputs = opt_cls._get_program_inputs(asdict(opt))
        self.assertDictEqual(inputs, expected)
        self.assertFalse(simulator, f"simulator not empty: {simulator}")

    @data(EstimatorOptions, SamplerOptions)
    def test_init_options_with_dictionary(self, opt_cls):
        """Test initializing options with dictionaries."""

        options_dicts = [
            {},
            {"dynamical_decoupling": "XX"},
            {"simulator": {"seed_simulator": 42}},
            {"environment": {"log_level": "WARNING"}},
            {
                "transpilation": {"optimization_level": 1},
                "execution": {"shots": 100},
            },
            {"twirling": {"gates": True, "strategy": "active"}},
            {"environment": {"log_level": "ERROR"}},
        ]

        for opts_dict in options_dicts:
            with self.subTest(opts_dict=opts_dict):
                options = asdict(opt_cls(**opts_dict))
                self.assertTrue(
                    dict_paritally_equal(options, opts_dict),
                    f"options={options}, opts_dict={opts_dict}",
                )

                # Make sure the structure didn't change.
                self.assertTrue(dict_keys_equal(asdict(opt_cls()), options), f"options={options}")

    @data(EstimatorOptions, SamplerOptions)
    def test_kwargs_options(self, opt_cls):
        """Test specifying arbitrary options."""
        with self.assertRaises(ValidationError) as exc:
            _ = opt_cls(foo="foo")  # pylint: disable=unexpected-keyword-arg
        self.assertIn("foo", str(exc.exception))

    @data(EstimatorOptions, SamplerOptions)
    def test_coupling_map_options(self, opt_cls):
        """Check that coupling_map is processed correctly for various types"""
        coupling_map = {(1, 0), (2, 1), (0, 1), (1, 2)}
        coupling_maps = [
            coupling_map,
            list(map(list, coupling_map)),
            CouplingMap(coupling_map),
        ]
        for variant in coupling_maps:
            with self.subTest(opts_dict=variant):
                options = opt_cls()
                options.simulator.coupling_map = variant
                inputs = opt_cls._get_program_inputs(asdict(options))
                resulting_cmap = inputs["transpilation"]["coupling_map"]
                self.assertEqual(coupling_map, set(map(tuple, resulting_cmap)))

    @combine(
        opt_cls=[EstimatorOptions, SamplerOptions], fake_backend=[FakeManila(), FakeNairobiV2()]
    )
    def test_simulator_set_backend(self, opt_cls, fake_backend):
        """Test Options.simulator.set_backend method."""

        options = opt_cls()
        options.simulator.seed_simulator = 42
        options.simulator.set_backend(fake_backend)

        noise_model = NoiseModel.from_backend(fake_backend)
        basis_gates = (
            fake_backend.configuration().basis_gates
            if isinstance(fake_backend, BackendV1)
            else fake_backend.operation_names
        )
        coupling_map = (
            fake_backend.configuration().coupling_map
            if isinstance(fake_backend, BackendV1)
            else fake_backend.coupling_map
        )

        self.assertEqual(options.simulator.coupling_map, coupling_map)
        self.assertEqual(options.simulator.noise_model, noise_model)

        expected_options = opt_cls()
        expected_options.simulator = {
            "noise_model": noise_model,
            "basis_gates": basis_gates,
            "coupling_map": coupling_map,
            "seed_simulator": 42,
        }

        self.assertDictEqual(asdict(options), asdict(expected_options))

    @combine(
        opt_cls=[EstimatorOptions, SamplerOptions],
        opt=[
            {"optimization_level": 99},
            {"resilience_level": 99},
            {"dynamical_decoupling": "foo"},
            {"transpilation": {"skip_transpilation": "foo"}},
            {"execution": {"shots": 0}},
            {"twirling": {"strategy": "foo"}},
            {"transpilation": {"foo": "bar"}},
            {"zne_noise_factors": [0.5]},
            {"noise_factors": [1, 3, 5]},
            {"zne_extrapolator": "exponential", "zne_noise_factors": [1]},
            {"zne_mitigation": True, "pec_mitigation": True},
            {"simulator": {"noise_model": "foo"}},
            {"shots": 1, "samples": 99, "shots_per_sample": 99},
            {"shots": 0},
        ],
    )
    def test_invalid_options(self, opt_cls, opt):
        """Test invalid inputs."""
        with self.assertRaises(ValidationError) as exc:
            opt_cls(**opt)
        self.assertIn(list(opt.keys())[0], str(exc.exception))

    @data(
        {"resilience_level": 2},
        {"max_execution_time": 200},
        {"resilience_level": 2, "transpilation": {"optimization_level": 1}},
        {"shots": 1024, "seed_simulator": 42},
        {"resilience_level": 2, "shots": 2048},
        {
            "optimization_level": 1,
            "transpilation": {"skip_transpilation": True},
            "log_level": "INFO",
        },
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
