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

from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime import Options, RuntimeOptions
from qiskit_ibm_runtime.options import EstimatorOptions, SamplerOptions
from qiskit_ibm_runtime.utils.qctrl import _warn_and_clean_options
from qiskit_ibm_runtime.fake_provider import FakeManila, FakeNairobiV2

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, dict_paritally_equal, combine


@ddt
class TestOptions(IBMTestCase):
    """Class for testing the Options class."""

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
                inputs = opt_cls._get_program_inputs(asdict(options))["options"]
                resulting_cmap = inputs["simulator"]["coupling_map"]
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
