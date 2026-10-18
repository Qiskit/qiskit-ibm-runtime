# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the noise learner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from qiskit import QuantumCircuit, transpile

from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
from qiskit_ibm_runtime.noise_learner import NoiseLearner
from qiskit_ibm_runtime.options import EstimatorOptions, NoiseLearnerOptions
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..registries import OneInstanceDryRunRegistry
from ..utils import get_mocked_backend

if TYPE_CHECKING:
    from collections.abc import Generator
    from unittest.mock import MagicMock

    from ..registries import BaseRegistry


def circuits() -> list[QuantumCircuit]:
    """Return a set of circuits, acting on two and three qubits."""
    c1 = QuantumCircuit(2)
    c1.cx(0, 1)

    c2 = QuantumCircuit(3)
    c2.cx(0, 1)
    c2.cx(1, 2)

    return [c1, c2]


@pytest.fixture
def equivalent_options() -> tuple[NoiseLearnerOptions, EstimatorOptions, dict[str, list[int]]]:
    """Return a set of non-trivial and equivalent learner, estimator, and dictionary options."""
    nl_options = NoiseLearnerOptions()
    nl_options.layer_pair_depths = [0, 2, 4]

    est_options = EstimatorOptions()
    est_options.resilience.layer_noise_learning.layer_pair_depths = [0, 2, 4]  # type: ignore[union-attr]
    est_options.resilience_level = 2

    dict_options = {"layer_pair_depths": [0, 2, 4]}

    return nl_options, est_options, dict_options


class TestNoiseLearner:
    """Class for testing the NoiseLearner class."""

    @pytest.mark.parametrize("task_type", ["circs", "pubs"])
    @pytest.mark.parametrize("options_type", ["learner", "estimator", "dict"])
    def test_run_program_inputs(
        self,
        task_type: str,
        options_type: str,
        equivalent_options: tuple[NoiseLearnerOptions, EstimatorOptions, dict],
    ) -> None:
        """Test all supported tasks and options types."""
        backend: MagicMock = get_mocked_backend()
        nl_options, est_options, dict_options = equivalent_options

        if task_type == "circs":
            tasks = [transpile(c) for c in circuits()]
        else:
            tasks = [(transpile(c), "Z" * c.num_qubits) for c in circuits()]

        if options_type == "learner":
            options: NoiseLearnerOptions | EstimatorOptions | dict = nl_options
        elif options_type == "estimator":
            options = est_options
        else:
            options = dict_options

        inst = NoiseLearner(backend, options)
        inst.run(tasks)

        input_params = backend.service._run.call_args.kwargs["inputs"]
        assert input_params["circuits"] == [transpile(c) for c in circuits()]

        expected = dict_options
        expected["support_qiskit"] = True
        assert input_params["options"] == expected

    @pytest.mark.parametrize("task_type", ["circs", "pubs", "circs_iterator", "pubs_iterator"])
    def test_run_program_inputs_with_default_options(self, task_type: str) -> None:
        """Test a circuit with default options.

        Also tests support for generators/iterators.
        """
        backend: MagicMock = get_mocked_backend()

        def circuit_generator(
            generated_circuits: list[QuantumCircuit],
        ) -> Generator[QuantumCircuit]:
            yield from generated_circuits

        def pub_generator(
            generated_circuits: list[QuantumCircuit],
        ) -> Generator[tuple[QuantumCircuit, str]]:
            for c in generated_circuits:
                yield (c, "Z" * c.num_qubits)

        if task_type == "circs":
            tasks: list[QuantumCircuit] | Generator[QuantumCircuit] = [
                transpile(c) for c in circuits()
            ]
        elif task_type == "circs_iterator":
            tasks = circuit_generator([transpile(c) for c in circuits()])
        elif task_type == "pubs":
            tasks = [(transpile(c), "Z" * c.num_qubits) for c in circuits()]
        else:
            tasks = pub_generator([transpile(c) for c in circuits()])

        inst = NoiseLearner(backend)
        inst.run(tasks)

        input_params = backend.service._run.call_args.kwargs["inputs"]
        assert input_params["circuits"] == [transpile(c) for c in circuits()]
        assert input_params["options"] == {"support_qiskit": True}

    def test_run_program_inputs_with_no_learnable_layers(self) -> None:
        """Test a circuit with no learnable layers."""
        backend: MagicMock = get_mocked_backend()

        inst = NoiseLearner(backend)
        inst.run([QuantumCircuit(3)])

        input_params = backend.service._run.call_args.kwargs["inputs"]
        assert "circuits" in input_params
        assert input_params["circuits"] == [QuantumCircuit(3)]

    def test_irrelevant_options_are_ignored(self) -> None:
        """Test that irrelevant estimator options are ignored."""
        backend: MagicMock = get_mocked_backend()

        options = EstimatorOptions()
        options.default_shots = 10
        options.default_precision = 0.1
        options.resilience.layer_noise_learning.num_randomizations = 2  # type: ignore[union-attr]

        expected = NoiseLearnerOptions()
        expected.num_randomizations = 2

        inst = NoiseLearner(backend, options)
        assert inst.options == expected

    def test_not_supported_in_local_mode(self) -> None:
        """Test exception when circuits is not ISA."""
        with pytest.raises(ValueError, match="not currently supported in local mode"):
            NoiseLearner(FakeSherbrooke())

    def test_get_backend(self) -> None:
        """Test getting the backend used."""
        backend = get_mocked_backend()
        inst = NoiseLearner(backend)
        assert inst.backend().name == backend.name

    @pytest.mark.registry(registry_class=OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry: BaseRegistry) -> None:
        """Noise Learner can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        noise_learner = NoiseLearner(mode=backend)
        job = noise_learner.run([transpile(c) for c in circuits()], dry_run=True)
        assert job.backend().name == "mock_foo"
