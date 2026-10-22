# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for client-side noise learner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError
from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.executor_noise_learner.noise_learner_v3 import NoiseLearnerV3
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.environment import EnvironmentOptions
from qiskit_ibm_runtime.options_models.execution import ExecutionOptions
from qiskit_ibm_runtime.options_models.noise_learner_v3 import NoiseLearnerV3Options
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.session import Session
from qiskit_ibm_runtime.utils.utils import HAS_QNL

from ...registries import OneInstanceDryRunRegistry

if TYPE_CHECKING:
    from ...registries import BaseRegistry


class TestNoiseLearnerUsingOptions:
    """Tests option setting on the ``NoiseLearnerV3`` class."""

    def test_default_options(self) -> None:
        """Test that default options are set when none are provided."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        assert isinstance(noise_learner.options, NoiseLearnerV3Options)
        assert noise_learner.options == NoiseLearnerV3Options()

    def test_options_from_instance(self) -> None:
        """Test constructing with an NoiseLearnerV3Options instance."""
        opts = NoiseLearnerV3Options(execution=ExecutionOptions(init_qubits=False))
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts)
        assert noise_learner.options is opts
        assert not noise_learner.options.execution.init_qubits

    def test_options_from_dict(self) -> None:
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts_dict)
        assert not noise_learner.options.execution.init_qubits
        assert noise_learner.options.execution.rep_delay == 0.5
        assert noise_learner.options.environment.log_level == "DEBUG"
        assert noise_learner.options.environment.job_tags == ["tag1"]

    def test_options_from_partial_dict(self) -> None:
        """Test constructing with a nested dict when only specifying some of the options."""
        noise_learner = NoiseLearnerV3(
            mode=FakeBrisbane(), options={"execution": {"init_qubits": False}}
        )
        assert not noise_learner.options.execution.init_qubits
        assert noise_learner.options.execution.rep_delay is None
        assert noise_learner.options.environment == EnvironmentOptions()

    def test_options_constructor_invalid_type(self) -> None:
        """Test that an invalid options type raises TypeError."""
        with pytest.raises(TypeError, match="Expected NoiseLearnerV3Options or dict"):
            NoiseLearnerV3(mode=FakeBrisbane(), options="invalid")  # type: ignore[arg-type]

    def test_setter_with_instance(self) -> None:
        """Test setting options via the setter with an NoiseLearnerV3Options instance."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        new_opts = NoiseLearnerV3Options(execution=ExecutionOptions(init_qubits=False))
        noise_learner.options = new_opts
        assert noise_learner.options is new_opts

    def test_setter_with_dict(self) -> None:
        """Test setting options via the setter with a dict."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        noise_learner.options = {"execution": {"init_qubits": False}}  # type: ignore[assignment]
        assert isinstance(noise_learner.options, NoiseLearnerV3Options)
        assert not noise_learner.options.execution.init_qubits

    def test_setter_invalid_type(self) -> None:
        """Test that setting options with an invalid type raises TypeError."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        with pytest.raises(TypeError, match="Expected NoiseLearnerV3Options or dict"):
            noise_learner.options = 42  # type: ignore[assignment]

    def test_setter_replaces_options(self) -> None:
        """Test that the setter replaces (not updates) the options."""
        noise_learner = NoiseLearnerV3(
            mode=FakeBrisbane(), options={"environment": {"log_level": "DEBUG"}}
        )
        noise_learner.options = {"execution": {"init_qubits": False}}  # type: ignore[assignment]
        # environment should be back to defaults since we replaced, not updated
        assert noise_learner.options.environment.log_level == "WARNING"
        assert not noise_learner.options.execution.init_qubits

    def test_experimental_options_default_empty(self) -> None:
        """Test that experimental options default to empty dict."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        assert noise_learner.options.experimental == {}

    def test_experimental_options_from_dict(self) -> None:
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts_dict)
        assert noise_learner.options.experimental == {"foo": "bar", "baz": 123}

    def test_experimental_options_from_instance(self) -> None:
        """Test constructing with an NoiseLearnerV3Options instance with experimental options."""
        opts = NoiseLearnerV3Options(experimental={"custom_key": "custom_value"})
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts)
        assert noise_learner.options.experimental == {"custom_key": "custom_value"}

    def test_experimental_options_setter(self) -> None:
        """Test setting experimental options via the setter."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        noise_learner.options = {"experimental": {"test": "value"}}  # type: ignore[assignment]
        assert noise_learner.options.experimental == {"test": "value"}

    def test_validation_on_mutation(self) -> None:
        """Test validation errors are raised on mutation, not just construction."""
        options = ExecutionOptions(init_qubits=False)
        with pytest.raises(ValidationError):
            options.init_qubits = [0, 1]  # type: ignore[assignment]

    def test_extra_variables_are_forbidden(self) -> None:
        """Test that we can not set variables undefined by the model."""
        options = ExecutionOptions()
        with pytest.raises(ValidationError):
            options.not_a_variable = 0  # type: ignore[attr-defined]


@pytest.mark.skipif(not HAS_QNL, reason="qiskit-noise-learning is required to run this test")
class TestNoiseLearnerRun:
    """Tests for the NoiseLearnerV3.run() method."""

    @pytest.mark.registry(registry_class=OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry: BaseRegistry) -> None:
        """NoiseLearnerV3 can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        noise_learner = NoiseLearnerV3(mode=backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pass_manager = generate_preset_pass_manager(optimization_level=0, backend=backend)
        pass_manager.post_scheduling = generate_boxing_pass_manager()
        boxed_circuit = pass_manager.run(circuit)
        layers = find_unique_box_instructions(boxed_circuit.data)

        job = noise_learner.run(layers, dry_run=True)
        assert job.backend().name == "mock_foo"

    @pytest.mark.parametrize("mode_id", ["job", "session", "batch"])
    def test_mode_handling(self, mode_id: str, registry: BaseRegistry) -> None:
        """NoiseLearnerV3 `mode` init argument should propagate to interface and through `run()`."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")

        match mode_id:
            case "job":
                mode = backend
                expected_mode = None
                expected_session_id = None
            case "session":
                mode = Session(backend)
                expected_mode = mode
                expected_session_id = "session_12345"
            case "batch":
                mode = Batch(backend)
                expected_mode = mode
                expected_session_id = "session_12345"

        # Public interfaces should respect `mode`.
        noise_learner = NoiseLearnerV3(mode=mode)
        assert noise_learner.backend() == backend
        assert noise_learner.mode == expected_mode

        # Jobs issued should belong to a session under `session` / `batch`` modes.
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pass_manager = generate_preset_pass_manager(optimization_level=0, backend=backend)
        pass_manager.post_scheduling = generate_boxing_pass_manager()
        boxed_circuit = pass_manager.run(circuit)
        layers = find_unique_box_instructions(boxed_circuit.data)

        job = noise_learner.run(layers)
        assert job._session_id == expected_session_id
