# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for local mode."""

import warnings

from ddt import data, ddt

from qiskit_aer import AerSimulator
from qiskit.primitives import (
    PrimitiveResult,
    PubResult,
    SamplerPubResult,
)
from qiskit.primitives.containers.data_bin import DataBin

from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime import (
    Session,
    Batch,
    SamplerV2,
    EstimatorV2,
)

from ..ibm_test_case import IBMTestCase
from ..utils import (
    get_primitive_inputs,
    combine,
)


@ddt
class TestLocalModeV2(IBMTestCase):
    """Class for testing local mode for V2 primitives."""

    def setUp(self) -> None:
        super().setUp()
        self._service = QiskitRuntimeLocalService()

    @combine(backend=[FakeManilaV2(), AerSimulator()], num_sets=[1, 3])
    def test_v2_sampler(self, backend, num_sets):
        """Test V2 Sampler on a local backend."""
        inst = SamplerV2(mode=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), num_sets)
        for pub_result in result:
            self.assertIsInstance(pub_result, SamplerPubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertIsInstance(pub_result.metadata, dict)
        self._service.delete_job(job.job_id())

    @combine(backend=[FakeManilaV2(), AerSimulator()], num_sets=[1, 3])
    def test_v2_estimator(self, backend, num_sets):
        """Test V2 Estimator on a local backend."""
        inst = EstimatorV2(mode=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), num_sets)
        for pub_result in result:
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertIsInstance(pub_result.metadata, dict)
        self._service.delete_job(job.job_id())

    @data(FakeManilaV2(), AerSimulator.from_backend(FakeManilaV2()))
    def test_v2_sampler_with_accepted_options(self, backend):
        """Test V2 sampler with accepted options."""
        options = {"default_shots": 10}
        inst = SamplerV2(mode=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        self.assertEqual(pub_result.data.meas.num_shots, 10)
        self.assertDictEqual(pub_result.data.meas.get_counts(), {"00011": 3, "00000": 7})
        self._service.delete_job(job.job_id())

    @data(FakeManilaV2(), AerSimulator.from_backend(FakeManilaV2()))
    def test_v2_estimator_with_accepted_options(self, backend):
        """Test V2 estimator with accepted options."""
        options = {"default_precision": 0.03125}
        inst = EstimatorV2(mode=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        self.assertIn(("target_precision", 0.03125), pub_result.metadata.items())
        self.assertEqual(pub_result.data.evs[0], 0.056640625)
        self._service.delete_job(job.job_id())

    @data(FakeManilaV2(), AerSimulator.from_backend(FakeManilaV2()))
    def test_v2_estimator_with_default_shots_option(self, backend):
        """Test V2 estimator with default shots converted to precision."""
        options = {"default_shots": 100}
        inst = EstimatorV2(mode=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        self.assertIn(("target_precision", 0.1), pub_result.metadata.items())
        self._service.delete_job(job.job_id())

    @combine(primitive=[SamplerV2, EstimatorV2], backend=[FakeManilaV2(), AerSimulator()])
    def test_primitive_v2_with_not_accepted_options(self, primitive, backend):
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
            self.assertIn("dynamical_decoupling", warning_messages)
        self._service.delete_job(job.job_id())

    @combine(session_cls=[Session, Batch], backend=[FakeManilaV2(), AerSimulator()])
    def test_sampler_v2_session(self, session_cls, backend):
        """Testing running v2 sampler inside session."""
        with session_cls(backend=backend) as session:
            inst = SamplerV2(mode=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            self.assertIsInstance(result, PrimitiveResult)
            self.assertEqual(len(result), 1)
            for pub_result in result:
                self.assertIsInstance(pub_result, PubResult)
                self.assertIsInstance(pub_result.data, DataBin)
                self.assertIsInstance(pub_result.metadata, dict)
        self._service.delete_job(job.job_id())

    @combine(session_cls=[Session, Batch], backend=[FakeManilaV2(), AerSimulator()])
    def test_sampler_v2_session_no_params(self, session_cls, backend):
        """Testing running v2 sampler inside session."""
        with session_cls(backend=backend):
            inst = SamplerV2()
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            self.assertIsInstance(result, PrimitiveResult)
            self.assertEqual(len(result), 1)
            for pub_result in result:
                self.assertIsInstance(pub_result, PubResult)
                self.assertIsInstance(pub_result.data, DataBin)
                self.assertIsInstance(pub_result.metadata, dict)
        self._service.delete_job(job.job_id())

    @combine(session_cls=[Session, Batch], backend=[FakeManilaV2(), AerSimulator()])
    def test_estimator_v2_session(self, session_cls, backend):
        """Testing running v2 estimator inside session."""
        with session_cls(backend=backend) as session:
            inst = EstimatorV2(mode=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            self.assertIsInstance(result, PrimitiveResult)
            self.assertEqual(len(result), 1)
            for pub_result in result:
                self.assertIsInstance(pub_result, PubResult)
                self.assertIsInstance(pub_result.data, DataBin)
                self.assertIsInstance(pub_result.metadata, dict)
        self._service.delete_job(job.job_id())

    @data(FakeManilaV2(), AerSimulator())
    def test_non_primitive(self, backend):
        """Test calling non-primitive in local mode."""
        session = Session(backend=backend)
        with self.assertRaisesRegex(ValueError, "Only sampler and estimator"):
            session.run(program_id="foo", inputs={})

    @combine(backend=[FakeManilaV2()])
    def test_retrieve_job(self, backend):
        """Test V2 Sampler on a local backend."""
        inst = SamplerV2(mode=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        job.result()
        rjob = self._service.job(job.job_id())
        self.assertEqual(rjob.job_id(), job.job_id())
        self._service.delete_job(job.job_id())

    @combine(backend=[FakeManilaV2()])
    def test_retrieve_jobs(self, backend):
        """Test V2 Sampler on a local backend."""
        inst = SamplerV2(mode=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        job.result()
        rjobs = self._service.jobs()
        self.assertIn(job.job_id(), [rjob.job_id() for rjob in rjobs])
        self._service.delete_job(job.job_id())

    @combine(backend=[FakeManilaV2()])
    def test_delete_job(self, backend):
        """Test V2 Sampler on a local backend."""
        inst = SamplerV2(mode=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        job.result()
        self._service.delete_job(job.job_id())
        self.assertNotIn(job.job_id(), [rjob.job_id() for rjob in self._service.jobs()])
