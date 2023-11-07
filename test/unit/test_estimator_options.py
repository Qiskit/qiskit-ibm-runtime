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

"""Tests for Options class."""

from dataclasses import asdict

from ddt import data, ddt
from pydantic import ValidationError
from qiskit.providers import BackendV1
from qiskit.providers.fake_provider import FakeManila, FakeNairobiV2
from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel

from qiskit_ibm_runtime.options.utils import merge_options
from qiskit_ibm_runtime.options import EstimatorOptions

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, dict_paritally_equal, flat_dict_partially_equal


@ddt
class TestEStimatorOptions(IBMTestCase):
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

    def test_program_inputs(self):
        """Test converting to program inputs from estimator options."""
        noise_model = NoiseModel.from_backend(FakeNairobiV2())
        options = EstimatorOptions(  # pylint: disable=unexpected-keyword-arg
            optimization_level=1,
            resilience_level=2,
            transpilation={"initial_layout": [1, 2], "skip_transpilation": True},
            execution={"shots": 100},
            environment={"log_level": "DEBUG"},
            simulator={"noise_model": noise_model},
            resilience={"zne_noise_factors": (1, 2, 4)},
        )
        inputs = EstimatorOptions._get_program_inputs(asdict(options))

        expected = {
            "execution": {"shots": 100, "noise_model": noise_model},
            "skip_transpilation": True,
            "transpilation": {
                "optimization_level": 1,
                "initial_layout": [1, 2],
            },
            "resilience_level": 2,
            "resilience": {
                "zne_noise_factors": (1.0, 2.0, 4.0),
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
            {"resilience_level": 1},
            {"simulator": {"seed_simulator": 42}},
            {"resilience_level": 1, "environment": {"log_level": "WARNING"}},
            {
                "transpilation": {"initial_layout": [1, 2], "layout_method": "trivial"},
                "execution": {"shots": 100},
            },
            {"environment": {"log_level": "ERROR"}},
        ]

        for opts_dict in options_dicts:
            with self.subTest(opts_dict=opts_dict):
                options = asdict(EstimatorOptions(**opts_dict))
                self.assertTrue(
                    dict_paritally_equal(options, opts_dict),
                    f"options={options}, opts_dict={opts_dict}",
                )

                # Make sure the structure didn't change.
                self.assertTrue(
                    dict_keys_equal(asdict(EstimatorOptions()), options), f"options={options}"
                )

    def test_kwargs_options(self):
        """Test specifying arbitrary options."""
        with self.assertRaises(ValidationError) as exc:
            _ = EstimatorOptions(foo="foo")  # pylint: disable=unexpected-keyword-arg
        self.assertIn("foo", str(exc.exception))

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
                options = EstimatorOptions()
                options.simulator.coupling_map = variant
                inputs = EstimatorOptions._get_program_inputs(asdict(options))
                resulting_cmap = inputs["transpilation"]["coupling_map"]
                self.assertEqual(coupling_map, set(map(tuple, resulting_cmap)))

    @data(
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
    )
    def test_bad_inputs(self, val):
        """Test invalid inputs."""
        with self.assertRaises(ValidationError) as exc:
            EstimatorOptions(**val)
        self.assertIn(list(val.keys())[0], str(exc.exception))

    @data(FakeManila(), FakeNairobiV2())
    def test_simulator_set_backend(self, fake_backend):
        """Test Options.simulator.set_backend method."""

        options = EstimatorOptions()
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

        expected_options = EstimatorOptions()
        expected_options.simulator = {
            "noise_model": noise_model,
            "basis_gates": basis_gates,
            "coupling_map": coupling_map,
            "seed_simulator": 42,
        }

        self.assertDictEqual(asdict(options), asdict(expected_options))
