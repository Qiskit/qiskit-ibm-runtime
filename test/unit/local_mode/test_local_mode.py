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

"""Tests for local mode."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import pytest
from qiskit.primitives import PrimitiveResult, PubResult, SamplerPubResult
from qiskit.primitives.containers.data_bin import DataBin
from qiskit_aer import AerSimulator

from qiskit_ibm_runtime import Batch, EstimatorV2, SamplerV2, Session
from qiskit_ibm_runtime.fake_provider import FakeManilaV2

from ...utils import get_primitive_inputs

if TYPE_CHECKING:
    from qiskit.providers import BackendV2


class TestLocalModeV2:
    """Class for testing local mode for V2 primitives."""

    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator()])
    @pytest.mark.parametrize("num_sets", [1, 3])
    def test_v2_sampler(self, backend: BackendV2, num_sets: int) -> None:
        """Test V2 Sampler on a local backend."""
        inst = SamplerV2(mode=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        assert isinstance(result, PrimitiveResult)
        assert len(result) == num_sets
        for pub_result in result:
            assert isinstance(pub_result, SamplerPubResult)
            assert isinstance(pub_result.data, DataBin)
            assert isinstance(pub_result.metadata, dict)

    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator()])
    @pytest.mark.parametrize("num_sets", [1, 3])
    def test_v2_estimator(self, backend: BackendV2, num_sets: int) -> None:
        """Test V2 Estimator on a local backend."""
        inst = EstimatorV2(mode=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        assert isinstance(result, PrimitiveResult)
        assert len(result) == num_sets
        for pub_result in result:
            assert isinstance(pub_result, PubResult)
            assert isinstance(pub_result.data, DataBin)
            assert isinstance(pub_result.metadata, dict)

    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator.from_backend(FakeManilaV2())])
    def test_v2_sampler_with_accepted_options(self, backend: BackendV2) -> None:
        """Test V2 sampler with accepted options."""
        options = {"default_shots": 10}
        inst = SamplerV2(mode=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        assert pub_result.data.meas.num_shots == 10

    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator.from_backend(FakeManilaV2())])
    def test_v2_estimator_with_accepted_options(self, backend: BackendV2) -> None:
        """Test V2 estimator with accepted options."""
        options = {"default_precision": 0.03125}
        inst = EstimatorV2(mode=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        assert ("target_precision", 0.03125) in pub_result.metadata.items()
        assert pub_result.data

    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator.from_backend(FakeManilaV2())])
    def test_v2_estimator_with_default_shots_option(self, backend: BackendV2) -> None:
        """Test V2 estimator with default shots converted to precision."""
        options = {"default_shots": 100}
        inst = EstimatorV2(mode=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        assert ("target_precision", 0.1) in pub_result.metadata.items()

    @pytest.mark.parametrize("primitive", [SamplerV2, EstimatorV2])
    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator()])
    def test_primitive_v2_with_not_accepted_options(
        self, primitive: type, backend: BackendV2
    ) -> None:
        """Test V2 primitive with not accepted options."""
        options = {
            "max_execution_time": 200,
            "dynamical_decoupling": {"enable": True},
            "simulator": {"seed_simulator": 42},
        }
        inst = primitive(mode=backend, options=options)
        with warnings.catch_warnings(record=True) as warns:
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            _ = job.result()
            warning_messages = "".join([str(warn.message) for warn in warns])
            assert "dynamical_decoupling" in warning_messages

    @pytest.mark.parametrize("session_cls", [Session, Batch])
    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator()])
    def test_sampler_v2_session(self, session_cls: type, backend: BackendV2) -> None:
        """Testing running v2 sampler inside session."""
        with session_cls(backend=backend) as session:
            inst = SamplerV2(mode=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            assert isinstance(result, PrimitiveResult)
            assert len(result) == 1
            for pub_result in result:
                assert isinstance(pub_result, PubResult)
                assert isinstance(pub_result.data, DataBin)
                assert isinstance(pub_result.metadata, dict)

    @pytest.mark.parametrize("session_cls", [Session, Batch])
    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator()])
    def test_sampler_v2_session_no_params(self, session_cls: type, backend: BackendV2) -> None:
        """Testing running v2 sampler inside session."""
        with session_cls(backend=backend):
            inst = SamplerV2()
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            assert isinstance(result, PrimitiveResult)
            assert len(result) == 1
            for pub_result in result:
                assert isinstance(pub_result, PubResult)
                assert isinstance(pub_result.data, DataBin)
                assert isinstance(pub_result.metadata, dict)

    @pytest.mark.parametrize("session_cls", [Session, Batch])
    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator()])
    def test_estimator_v2_session(self, session_cls: type, backend: BackendV2) -> None:
        """Testing running v2 estimator inside session."""
        with session_cls(backend=backend) as session:
            inst = EstimatorV2(mode=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            assert isinstance(result, PrimitiveResult)
            assert len(result) == 1
            for pub_result in result:
                assert isinstance(pub_result, PubResult)
                assert isinstance(pub_result.data, DataBin)
                assert isinstance(pub_result.metadata, dict)

    @pytest.mark.parametrize("backend", [FakeManilaV2(), AerSimulator()])
    def test_non_primitive(self, backend: BackendV2) -> None:
        """Test calling non-primitive in local mode."""
        session = Session(backend=backend)
        with pytest.raises(ValueError, match="Only sampler and estimator"):
            session._run(program_id="foo", inputs={})
