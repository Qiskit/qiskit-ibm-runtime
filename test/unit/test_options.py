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
from qiskit.providers import BackendV1
from qiskit.providers.fake_provider import FakeManila, FakeNairobiV2
from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime import Options, RuntimeOptions
from qiskit_ibm_runtime.utils.qctrl import _warn_and_clean_options

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, dict_paritally_equal, flat_dict_partially_equal


@ddt
class TestOptions(IBMTestCase):
    """Class for testing the Sampler class."""

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
                combined = Options._merge_options(asdict(options), new_ops)

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
            resilience={"noise_factors": (0, 2, 4)},
        )
        inputs = Options._get_program_inputs(asdict(options))

        expected = {
            "execution": {"shots": 100, "noise_model": noise_model},
            "skip_transpilation": True,
            "transpilation": {
                "optimization_level": 1,
                "initial_layout": [1, 2],
            },
            "resilience_level": 2,
            "resilience": {
                "noise_factors": (0, 2, 4),
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

    def test_backend_in_options(self):
        """Test specifying backend in options."""
        backend_name = "ibm_gotham"
        backend = FakeManila()
        backend._instance = None
        backend.name = backend_name
        backends = [backend_name, backend]
        for backend in backends:
            with self.assertRaises(TypeError) as exc:
                _ = Options(backend=backend)  # pylint: disable=unexpected-keyword-arg
            self.assertIn(
                "__init__() got an unexpected keyword argument 'backend'",
                str(exc.exception),
            )

    def test_unsupported_options(self):
        """Test error on unsupported second level options"""
        # defining minimal dict of options
        options = {
            "optimization_level": 1,
            "resilience_level": 2,
            "dynamical_decoupling": "XX",
            "transpilation": {"initial_layout": [1, 2], "skip_transpilation": True},
            "execution": {"shots": 100},
            "environment": {"log_level": "DEBUG"},
            "simulator": {"noise_model": "model"},
            "resilience": {
                "noise_factors": (0, 2, 4),
                "extrapolator": "LinearExtrapolator",
            },
            "twirling": {},
        }
        Options.validate_options(options)
        for opt in ["simulator", "transpilation", "execution"]:
            temp_options = options.copy()
            temp_options[opt] = {"aaa": "bbb"}
            with self.assertRaises(ValueError) as exc:
                Options.validate_options(temp_options)
            self.assertIn(f"Unsupported value 'aaa' for {opt}.", str(exc.exception))

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
                resulting_cmap = inputs["transpilation"]["coupling_map"]
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

    def test_merge_with_defaults_overwrite(self):
        """Test merge_with_defaults with different overwrite."""
        expected = {"twirling": {"measure": True}}
        all_options = [
            ({"twirling": {"measure": True}}, {}),
            ({}, {"twirling": {"measure": True}}),
            ({"twirling": {"measure": False}}, {"twirling": {"measure": True}}),
        ]

        for old, new in all_options:
            with self.subTest(old=old, new=new):
                old["resilience_level"] = 0
                final = Options._merge_options_with_defaults(old, new)
                self.assertTrue(dict_paritally_equal(final, expected))
                self.assertEqual(final["resilience_level"], 0)
                res_dict = final["resilience"]
                self.assertFalse(res_dict["measure_noise_mitigation"])
                self.assertFalse(res_dict["zne_mitigation"])
                self.assertFalse(res_dict["pec_mitigation"])

    def test_merge_with_defaults_different_level(self):
        """Test merge_with_defaults with different resilience level."""

        old = {"resilience_level": 0}
        new = {"resilience_level": 3, "measure_noise_mitigation": False}
        final = Options._merge_options_with_defaults(old, new)
        self.assertEqual(final["resilience_level"], 3)
        res_dict = final["resilience"]
        self.assertFalse(res_dict["measure_noise_mitigation"])
        self.assertFalse(res_dict["zne_mitigation"])
        self.assertTrue(res_dict["pec_mitigation"])

    def test_merge_with_defaults_noiseless_simulator(self):
        """Test merge_with_defaults with noiseless simulator."""

        new = {"measure_noise_mitigation": True}
        final = Options._merge_options_with_defaults({}, new, is_simulator=True)
        self.assertEqual(final["resilience_level"], 0)
        self.assertEqual(final["optimization_level"], 1)
        res_dict = final["resilience"]
        self.assertTrue(res_dict["measure_noise_mitigation"])
        self.assertFalse(res_dict["zne_mitigation"])
        self.assertFalse(res_dict["pec_mitigation"])

    def test_merge_with_defaults_noisy_simulator(self):
        """Test merge_with_defaults with noisy simulator."""

        new = {"measure_noise_mitigation": False}
        final = Options._merge_options_with_defaults(
            {"simulator": {"noise_model": "foo"}}, new, is_simulator=True
        )
        self.assertEqual(final["resilience_level"], 1)
        self.assertEqual(final["optimization_level"], 3)
        res_dict = final["resilience"]
        self.assertFalse(res_dict["measure_noise_mitigation"])
        self.assertFalse(res_dict["zne_mitigation"])
        self.assertFalse(res_dict["pec_mitigation"])
