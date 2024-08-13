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

from qiskit_ibm_runtime import RuntimeOptions
from qiskit_ibm_runtime.options import EstimatorOptions, SamplerOptions
from qiskit_ibm_runtime.fake_provider import FakeManila, FakeNairobiV2

from ..ibm_test_case import IBMTestCase
from ..utils import combine


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
