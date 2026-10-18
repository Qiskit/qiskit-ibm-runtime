# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for estimator class."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import real_amplitudes
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import Pauli, SparsePauliOp

from qiskit_ibm_runtime import EstimatorOptions, EstimatorV2, IBMInputValueError, Session
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..asserts import assert_dict_partially_equal, assert_warns_strict
from ..registries import OneInstanceDryRunRegistry
from ..utils import (
    get_mocked_backend,
    get_primitive_inputs,
    get_transpiled_circuit,
    remap_observables,
    transpile_pubs,
)

if TYPE_CHECKING:
    from ..registries import BaseRegistry


class TestEstimatorV2:
    """Class for testing the Estimator class."""

    @pytest.mark.parametrize(
        "abs_pubs",
        [
            [(real_amplitudes(num_qubits=2, reps=1), ["ZZ"], [[1, 2, 3, 4]])],
            [(real_amplitudes(num_qubits=2, reps=1), ["ZZ", "YY"], [[1, 2, 3, 4]])],
            [(QuantumCircuit(2), ["XX"])],
            [
                (real_amplitudes(num_qubits=1, reps=1), ["I"], [[1, 2]]),
                (QuantumCircuit(3), ["YYY"]),
            ],
        ],
    )
    def test_run_program_inputs(self, abs_pubs: list) -> None:
        """Verify program inputs are correct."""
        backend = get_mocked_backend()
        t_pubs = transpile_pubs(abs_pubs, backend, "estimator")

        inst = EstimatorV2(mode=backend)
        inst.run(t_pubs)
        input_params = backend.service._run.call_args.kwargs["inputs"]  # type: ignore[attr-defined]
        assert "pubs" in input_params
        pubs_param = input_params["pubs"]
        for a_pub_param, an_in_taks in zip(pubs_param, t_pubs):
            assert isinstance(a_pub_param, EstimatorPub)
            # Check circuit
            assert a_pub_param.circuit == an_in_taks[0]
            # Check observables
            for a_pub_obs, an_input_obs in zip(a_pub_param.observables.tolist(), an_in_taks[1]):
                assert list(a_pub_obs.keys())[0] == an_input_obs
            # Check parameter values
            an_input_params = an_in_taks[2] if len(an_in_taks) == 3 else []
            param_values_array = list(a_pub_param.parameter_values.data.values())
            a_pub_param_values = param_values_array[0] if param_values_array else param_values_array
            np.testing.assert_allclose(a_pub_param_values, an_input_params)

    def test_unsupported_values_for_estimator_options(self) -> None:
        """Test exception when options levels are not supported."""
        options_bad = [
            {
                "resilience_level": 4,
            },
        ]

        backend = get_mocked_backend()
        with Session(
            backend=backend,
        ) as session:
            for bad_opt in options_bad:
                inst = EstimatorV2(mode=session)
                with pytest.raises(ValueError) as exc:
                    inst.options.update(**bad_opt)
                assert list(bad_opt.keys())[0] in str(exc.value)

    def test_invalid_estimator_precision_option(self) -> None:
        """Test exception when precision is invalid."""
        backend = get_mocked_backend()
        backend.configuration().simulator = True

        estimator = EstimatorV2(mode=backend)
        with pytest.raises(ValueError) as exc:
            estimator.run(**get_primitive_inputs(estimator), precision=0)
        assert "The precision value must be strictly greater than 0" in str(exc.value)

    def test_invalid_estimator_pub_precision(self) -> None:
        """Test exception when a pub specifies a precision that is not strictly greater than 0."""
        backend = get_mocked_backend()
        backend.configuration().simulator = True

        estimator = EstimatorV2(mode=backend)
        # Precision supplied at the pub level (4th element) must also be guarded client-side,
        # not just the run() kwarg -- otherwise a pub-level precision=0 reaches the server and
        # raises a bare ZeroDivisionError when it converts precision to shots.
        pub = get_primitive_inputs(estimator)["pubs"][0]
        pub_with_zero_precision = (*pub, 0)
        with pytest.raises(ValueError, match="The precision value must be strictly greater than 0"):
            estimator.run([pub_with_zero_precision])

    def test_pec_simulator(self) -> None:
        """Test error is raised when using pec on simulator without coupling map."""
        backend = get_mocked_backend()
        backend.configuration().simulator = True

        inst = EstimatorV2(mode=backend, options={"resilience": {"pec_mitigation": True}})
        with pytest.raises(ValueError) as exc:
            inst.run(**get_primitive_inputs(inst))
        assert "coupling map" in str(exc.value)

    @pytest.mark.parametrize(
        ("options", "expected"),
        [
            (
                EstimatorOptions(default_shots=1024),  # type: ignore[call-arg]
                {"default_shots": 1024},
            ),
            (
                {
                    "default_precision": 0.1,
                    "dynamical_decoupling": {"enable": True},
                },
                {
                    "default_precision": 0.1,
                    "dynamical_decoupling": {"enable": True},
                },
            ),
        ],
    )
    def test_run_default_options(self, options: dict, expected: dict) -> None:
        """Test run using default options."""
        backend = get_mocked_backend()

        inst = EstimatorV2(mode=backend, options=options)
        inst.run(**get_primitive_inputs(inst, backend=backend))

        run_options = backend.service._run.call_args.kwargs["inputs"]["options"]  # type: ignore[attr-defined]
        assert_dict_partially_equal(run_options, expected)

    @pytest.mark.parametrize(
        "res_opt",
        [
            {"zne_extrapolator": "bad_extrapolator"},
            {"zne_extrapolator": "double_exponential", "zne_noise_factors": [1]},
        ],
    )
    def test_invalid_resilience_options(self, res_opt: dict) -> None:
        """Test invalid resilience options."""
        backend = get_mocked_backend()
        with pytest.raises(ValueError) as exc:
            inst = EstimatorV2(mode=backend, options={"resilience": res_opt})
            inst.run(**get_primitive_inputs(inst, backend))
        assert list(res_opt.values())[0] in str(exc.value)
        if len(res_opt.keys()) > 1:
            assert list(res_opt.keys())[1] in str(exc.value)

    @pytest.mark.parametrize(
        "observables",
        [
            "IX",
            Pauli("YZ"),
            SparsePauliOp(["IX", "YZ"]),
            {"YZ": 1 + 2j},
            {Pauli("XX"): 1 + 2j},
            ["XX", "YY"],
            [Pauli("XX"), Pauli("YY")],
            [SparsePauliOp(["XX"], [2]), SparsePauliOp(["YY"], [1])],
            [
                {"XX": 1},
                {"YY": 2},
            ],
            [
                {Pauli("XX"): 1},
                {Pauli("YY"): 2},
            ],
        ],
    )
    def test_observable_types_single_circuit(self, observables: object) -> None:
        """Test different observable types for a single circuit."""
        backend = get_mocked_backend()
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        isa_circuit = transpile(circuit, backend=backend)

        estimator = EstimatorV2(mode=backend)
        pub = (isa_circuit, remap_observables(observables, isa_circuit))  # type: ignore[arg-type]
        estimator.run([pub])

    @pytest.mark.parametrize(
        "observables",
        [
            ["XX", "YYY"],
            [Pauli("XX"), Pauli("YYY")],
            [SparsePauliOp(["XX"]), SparsePauliOp(["YYY"])],
            [
                {"XX": 1 + 2j},
                {"YYY": 1 + 2j},
            ],
            [
                {Pauli("XX"): 1 + 2j},
                {Pauli("YYY"): 1 + 2j},
            ],
            [["XX", "YY"], ["ZZZ", "III"]],
            [[Pauli("XX"), Pauli("YY")], [Pauli("XXX"), Pauli("YYY")]],
            [
                [SparsePauliOp(["XX", "YY"], [1, 2]), SparsePauliOp(["YY", "-XX"], [2, 1])],
                [SparsePauliOp(["XXX"], [1]), SparsePauliOp(["YYY"], [2])],
            ],
            [[{"XX": 1}, {"YY": 2}], [{"XXX": 1}, {"YYY": 2}]],
            [
                [{Pauli("XX"): 1}, {Pauli("YY"): 2}],
                [{Pauli("XXX"): 1}, {Pauli("YYY"): 2}],
            ],
        ],
    )
    def test_observable_types_multi_circuits(self, observables: object) -> None:
        """Test different observable types for multiple circuits."""
        backend = get_mocked_backend()
        circuit1 = get_transpiled_circuit(backend, num_qubits=2, measure=False)
        circuit2 = get_transpiled_circuit(backend, num_qubits=3, measure=False)

        estimator = EstimatorV2(mode=backend)
        obs1 = remap_observables(observables[0], circuit1)  # type: ignore[index]
        obs2 = remap_observables(observables[1], circuit2)  # type: ignore[index]
        estimator.run(pubs=[(circuit1, obs1), (circuit2, obs2)])

    @pytest.mark.parametrize(
        "observables",
        [
            ["Y0"],
            {"1X": 2},
            [["rZ", "YY"]],
            [
                [
                    {"XX": 3},
                    {"++": 4},
                ]
            ],
        ],
    )
    def test_invalid_basis(self, observables: object) -> None:
        """Test observable containing invalid basis."""
        circuit = QuantumCircuit(2)
        estimator = EstimatorV2(mode=get_mocked_backend())

        with pytest.raises(ValueError, match="Observable"):
            estimator.run([(circuit, observables)])

    def test_unsupported_dynamical_decoupling_with_dynamic_circuits(self) -> None:
        """Test running on dynamic circuits with dynamical decoupling enabled is not allowed."""
        dynamic_circuit = QuantumCircuit(3, 1)
        dynamic_circuit.h(0)
        dynamic_circuit.measure(0, 0)
        dynamic_circuit.if_else(
            (0, True), QuantumCircuit(3, 1), QuantumCircuit(3, 1), [0, 1, 2], [0]
        )

        in_pubs = [(dynamic_circuit, ["XXX"])]
        backend = get_mocked_backend()
        inst = EstimatorV2(mode=backend)
        inst.options.dynamical_decoupling.enable = True  # type: ignore[union-attr]
        with pytest.raises(
            IBMInputValueError,
            match="Dynamical decoupling currently cannot be used with dynamic circuits",
        ):
            inst.run(in_pubs)

    def test_estimator_validations(self) -> None:
        """Test exceptions when failing client-side validations."""
        backend = get_mocked_backend()
        inst = EstimatorV2(mode=backend)
        circ = QuantumCircuit(2)
        obs: list[object] = []
        with pytest.raises(IBMInputValueError, match="Empty observables array is not allowed"):
            inst.run(pubs=[(circ, obs)])

    def test_gate_not_in_target(self) -> None:
        """Test exception when circuits contain gates that are not basis gates."""
        backend = FakeSherbrooke()
        estimator = EstimatorV2(mode=backend)
        observable = SparsePauliOp("Z")

        circ = QuantumCircuit(1, 1)
        circ.x(0)
        circ.measure(0, 0)
        with circ.if_test((0, 1)):
            with circ.if_test((0, 0)) as else_:
                circ.x(0)
            with else_:
                circ.h(0)
        circ.measure(0, 0)

        with pytest.raises(IBMInputValueError, match=" h "):
            estimator.run(pubs=[(circ, observable)])

    @pytest.mark.parametrize(
        ("pub_precisions", "run_precision", "num_appearances"),
        [
            ([None, None], 0.01, 0),
            ([0.01, 0.01], 0.01, 0),
            ([0.02, 0.02], 0.01, 0),
            ([0.02, None], 0.02, 0),
            ([0.02, None], 0.01, 1),
            ([0.01, 0.02, 0.03], 0.04, 1),
        ],
    )
    def test_deprecate_pub_level_precision(
        self, pub_precisions: list[float], run_precision: float, num_appearances: int
    ) -> None:
        """Conflicting pub-level precision emits one DeprecationWarning."""
        backend = get_mocked_backend()
        circ = QuantumCircuit(1)
        t_circ = transpile(circ, backend=backend)
        observable = remap_observables("Z", t_circ)
        inst = EstimatorV2(mode=backend)

        warning_msg = "Specifying different 'precision' across pubs is deprecated"
        pubs = [
            (t_circ, observable, None, precision)
            if precision is not None
            else EstimatorPub.coerce((t_circ, observable))
            for precision in pub_precisions
        ]

        with assert_warns_strict(DeprecationWarning, warning_msg, num_appearances):
            inst.run(pubs, precision=run_precision)

    @pytest.mark.registry(registry_class=OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry: BaseRegistry) -> None:
        """Estimator can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        estimator = EstimatorV2(mode=backend)
        job = estimator.run(**get_primitive_inputs(estimator, backend=backend), dry_run=True)
        assert job.backend().name == "mock_foo"
