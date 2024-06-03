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
    EstimatorResult,
    SamplerResult,
    PrimitiveResult,
    PubResult,
    SamplerPubResult,
)
from qiskit.primitives.containers.data_bin import DataBin

from qiskit_ibm_runtime.fake_provider import FakeManila, FakeManilaV2
from qiskit_ibm_runtime import (
    Sampler,
    Estimator,
    Options,
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
class TestLocalModeV1(IBMTestCase):
    """Class for testing local mode for v1 primitives."""

    @combine(backend=[FakeManila(), FakeManilaV2(), AerSimulator()], num_sets=[1, 3])
    def test_v1_sampler(self, backend, num_sets):
        """Test V1 Sampler on a local backend."""
        inst = Sampler(backend=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        self.assertIsInstance(result, SamplerResult)
        self.assertEqual(len(result.quasi_dists), num_sets)
        self.assertEqual(len(result.metadata), num_sets)

    @combine(backend=[FakeManila(), FakeManilaV2(), AerSimulator()], num_sets=[1, 3])
    def test_v1_estimator(self, backend, num_sets):
        """Test V1 Estimator on a local backend."""
        inst = Estimator(backend=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        self.assertIsInstance(result, EstimatorResult)
        self.assertEqual(len(result.values), num_sets)
        self.assertEqual(len(result.metadata), num_sets)

    @data(FakeManila(), FakeManilaV2(), AerSimulator())
    def test_v1_sampler_with_accepted_options(self, backend):
        """Test V1 sampler with accepted options."""
        shots = 2000
        options = Options(
            execution={"shots": shots},
            transpilation={"skip_transpilation": True},
            simulator={"seed_simulator": 42},
        )
        inst = Sampler(backend=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        result = job.result()
        self.assertEqual(result.metadata[0]["shots"], shots)
        self.assertDictEqual(result.quasi_dists[0], {1: 0.002, 2: 0.001, 0: 0.504, 3: 0.493})

    @data(FakeManila(), FakeManilaV2(), AerSimulator())
    def test_v1_estimator_with_accepted_options(self, backend):
        """Test V1 estimator with accepted options."""
        shots = 2000
        options = Options(
            execution={"shots": shots},
            transpilation={"skip_transpilation": True},
            simulator={"seed_simulator": 42},
        )
        inst = Estimator(backend=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        result = job.result()
        self.assertEqual(result.metadata[0]["shots"], shots)
        self.assertEqual(result.values[0], 0.01)

    @combine(primitive=[Sampler, Estimator], backend=[FakeManila(), FakeManilaV2(), AerSimulator()])
    def test_primitve_v1_with_not_accepted_options(self, primitive, backend):
        """Test V1 primitive with accepted options."""
        shots = 2000
        options = Options(execution={"shots": shots}, resilience_level=1, max_execution_time=200)
        inst = primitive(backend=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        result = job.result()
        self.assertEqual(result.metadata[0]["shots"], shots)

    @combine(session_cls=[Session, Batch], backend=[FakeManila(), FakeManilaV2(), AerSimulator()])
    def test_sampler_v1_session(self, session_cls, backend):
        """Testing running v1 sampler inside session."""
        with session_cls(backend=backend) as session:
            inst = Sampler(session=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)

    @combine(session_cls=[Session, Batch], backend=[FakeManila(), FakeManilaV2(), AerSimulator()])
    def test_estimator_v1_session(self, session_cls, backend):
        """Testing running v1 estimator inside session."""
        with session_cls(backend=backend) as session:
            inst = Estimator(session=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            self.assertIsInstance(result, EstimatorResult)
            self.assertEqual(len(result.values), 1)
            self.assertEqual(len(result.metadata), 1)


@ddt
class TestLocalModeV2(IBMTestCase):
    """Class for testing local mode for V2 primitives."""

    @combine(backend=[FakeManila(), FakeManilaV2(), AerSimulator()], num_sets=[1, 3])
    def test_v2_sampler(self, backend, num_sets):
        """Test V2 Sampler on a local backend."""
        inst = SamplerV2(backend=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), num_sets)
        for pub_result in result:
            self.assertIsInstance(pub_result, SamplerPubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertIsInstance(pub_result.metadata, dict)

    @combine(backend=[FakeManila(), FakeManilaV2(), AerSimulator()], num_sets=[1, 3])
    def test_v2_estimator(self, backend, num_sets):
        """Test V2 Estimator on a local backend."""
        inst = EstimatorV2(backend=backend)
        job = inst.run(**get_primitive_inputs(inst, backend=backend, num_sets=num_sets))
        result = job.result()
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), num_sets)
        for pub_result in result:
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertIsInstance(pub_result.metadata, dict)

    @data(FakeManila(), FakeManilaV2(), AerSimulator.from_backend(FakeManila()))
    def test_v2_sampler_with_accepted_options(self, backend):
        """Test V2 sampler with accepted options."""
        options = {"default_shots": 10, "simulator": {"seed_simulator": 42}}
        inst = SamplerV2(backend=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        self.assertEqual(pub_result.data.meas.num_shots, 10)
        self.assertDictEqual(pub_result.data.meas.get_counts(), {"00011": 3, "00000": 7})

    @data(FakeManila(), FakeManilaV2(), AerSimulator.from_backend(FakeManila()))
    def test_v2_estimator_with_accepted_options(self, backend):
        """Test V1 estimator with accepted options."""
        options = {"default_precision": 0.03125, "simulator": {"seed_simulator": 42}}
        inst = EstimatorV2(backend=backend, options=options)
        job = inst.run(**get_primitive_inputs(inst, backend=backend))
        pub_result = job.result()[0]
        self.assertDictEqual(pub_result.metadata, {"target_precision": 0.03125})
        self.assertEqual(pub_result.data.evs[0], 0.056640625)

    @combine(
        primitive=[SamplerV2, EstimatorV2], backend=[FakeManila(), FakeManilaV2(), AerSimulator()]
    )
    def test_primitive_v2_with_not_accepted_options(self, primitive, backend):
        """Test V1 primitive with accepted options."""
        options = {
            "max_execution_time": 200,
            "dynamical_decoupling": {"enable": True},
            "simulator": {"seed_simulator": 42},
        }
        inst = primitive(backend=backend, options=options)
        with warnings.catch_warnings(record=True) as warns:
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            _ = job.result()
            self.assertEqual(len(warns), 1)
            self.assertIn("dynamical_decoupling", str(warns[0].message))

    @combine(session_cls=[Session, Batch], backend=[FakeManila(), FakeManilaV2(), AerSimulator()])
    def test_sampler_v2_session(self, session_cls, backend):
        """Testing running v2 sampler inside session."""
        with session_cls(backend=backend) as session:
            inst = SamplerV2(session=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            self.assertIsInstance(result, PrimitiveResult)
            self.assertEqual(len(result), 1)
            for pub_result in result:
                self.assertIsInstance(pub_result, PubResult)
                self.assertIsInstance(pub_result.data, DataBin)
                self.assertIsInstance(pub_result.metadata, dict)

    @combine(session_cls=[Session, Batch], backend=[FakeManila(), FakeManilaV2(), AerSimulator()])
    def test_estimator_v2_session(self, session_cls, backend):
        """Testing running v2 estimator inside session."""
        with session_cls(backend=backend) as session:
            inst = EstimatorV2(session=session)
            job = inst.run(**get_primitive_inputs(inst, backend=backend))
            result = job.result()
            self.assertIsInstance(result, PrimitiveResult)
            self.assertEqual(len(result), 1)
            for pub_result in result:
                self.assertIsInstance(pub_result, PubResult)
                self.assertIsInstance(pub_result.data, DataBin)
                self.assertIsInstance(pub_result.metadata, dict)

    @data(FakeManila(), FakeManilaV2(), AerSimulator())
    def test_non_primitive(self, backend):
        """Test calling non-primitive in local mode."""
        session = Session(backend=backend)
        with self.assertRaisesRegex(ValueError, "Only sampler and estimator"):
            session.run(program_id="foo", inputs={})
