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

"""Tests for primitive classes."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

import numpy as np
import pytest
from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import real_amplitudes
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime import Batch, QiskitRuntimeService, Session
from qiskit_ibm_runtime.base_primitive import get_mode_service_backend
from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeVigoV2
from qiskit_ibm_runtime.server_side import EstimatorV2, SamplerV2
from qiskit_ibm_runtime.server_side.estimator import Estimator as IBMBaseEstimator

from ..asserts import (
    assert_dict_flat_partially_equal,
    assert_dict_keys_equal,
    assert_dict_partially_equal,
)
from ..registries import get_submitted_jobs
from ..utils import create_faulty_backend, get_primitive_inputs

if TYPE_CHECKING:
    from responses import RequestsMock

    from ..registries import BaseRegistry


@pytest.mark.server_side_primitives
class TestPrimitivesV2:
    """Class for testing the Sampler and Estimator classes."""

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_dict_options(self, primitive: type[EstimatorV2 | SamplerV2]) -> None:
        """Test passing a dictionary as options."""
        options_vars: list[dict] = [
            {},
            {
                "max_execution_time": 100,
                "execution": {"init_qubits": True},
            },
            {"default_shots": 1000},
        ]
        backend = FakeVigoV2()
        for options in options_vars:
            inst = primitive(mode=backend, options=options)
            assert_dict_partially_equal(asdict(inst.options), options)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize(
        "env_var",
        [
            {"log_level": "DEBUG"},
            {"job_tags": ["foo", "bar"]},
        ],
    )
    def test_runtime_options(self, primitive: type[EstimatorV2 | SamplerV2], env_var: dict) -> None:
        """Test RuntimeOptions specified as primitive options."""
        options = primitive._options_class(environment=env_var)  # type: ignore[call-arg]
        run_options = primitive._options_class._get_runtime_options(asdict(options))
        for key, val in env_var.items():
            assert run_options[key] == val

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize(
        "opts",
        [
            {"experimental": {"image": "foo:bar"}},
            {"experimental": {"image": "foo:bar"}, "environment": {"log_level": "INFO"}},
        ],
    )
    def test_image(self, primitive: type[EstimatorV2 | SamplerV2], opts: dict) -> None:
        """Test passing an image to options."""
        options = primitive._options_class(**opts)
        options_dict = asdict(options)
        run_options = primitive._options_class._get_runtime_options(options_dict)
        input_params = primitive._options_class._get_program_inputs(options_dict)
        expected = list(opts.values())[0]
        for key, val in expected.items():
            assert run_options[key] == val
            assert key not in input_params
            assert key not in input_params["options"]
            assert key not in input_params["options"].get("experimental", {})

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_options_copied(self, primitive: type) -> None:
        """Test modifying original options does not affect primitives."""
        backend = FakeVigoV2()
        options = primitive._options_class()  # type: ignore[attr-defined]
        options.max_execution_time = 100
        inst = primitive(mode=backend, options=options)
        options.max_execution_time = 200
        assert inst.options.max_execution_time == 100

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_init_with_backend_instance(
        self, primitive: type, registry: BaseRegistry, responses: RequestsMock
    ) -> None:
        """Test initializing a primitive with a backend instance."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")

        inst = primitive(mode=backend)
        assert inst.mode is None
        inst.run(**get_primitive_inputs(inst, backend=backend))

        jobs = get_submitted_jobs(responses)
        assert len(jobs) == 1
        assert jobs[0]["backend"] == backend.name

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_init_with_backend_session(self, primitive: type, registry: BaseRegistry) -> None:
        """Test initializing a primitive with both backend and session."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")

        session = Session(backend)
        inst = primitive(mode=session)
        assert inst.mode is not None
        job = inst.run(**get_primitive_inputs(inst))
        assert job.session_id == "session_12345"

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_default_session_context_manager(self, primitive: type, registry: BaseRegistry) -> None:
        """Test getting default session within context manager."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")

        with Session(backend=backend) as session:
            inst = primitive()
            assert inst.mode == session
            assert inst.mode.backend() == "common_backend"

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_default_session_cm_new_backend(self, primitive: type, registry: BaseRegistry) -> None:
        """Test using a different backend within context manager."""
        service = QiskitRuntimeService(token="my_token")
        session_backend = service.backend("unique_backend_a")
        backend = service.backend("common_backend")

        with Session(backend=session_backend):
            with pytest.raises(ValueError):
                _ = primitive(mode=backend)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_no_session(
        self, primitive: type, registry: BaseRegistry, responses: RequestsMock
    ) -> None:
        """Test running without session."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        inst = primitive(backend)
        inst.run(**get_primitive_inputs(inst, backend=backend))
        assert inst.mode is None

        jobs = get_submitted_jobs(responses)
        assert len(jobs) == 1
        assert "session_id" not in jobs[0]
        assert "start_session" not in jobs[0]

    @pytest.mark.parametrize("primitive", [SamplerV2, EstimatorV2])
    def test_init_with_mode_as_backend(
        self, primitive: type, registry: BaseRegistry, responses: RequestsMock
    ) -> None:
        """Test initializing a primitive with mode as a Backend."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")

        inst = primitive(mode=backend)
        assert inst is not None
        inst.run(**get_primitive_inputs(inst, backend=backend))

        jobs = get_submitted_jobs(responses)
        assert len(jobs) == 1
        assert jobs[0]["backend"] == backend.name

    @pytest.mark.parametrize("primitive", [SamplerV2, EstimatorV2])
    def test_init_with_mode_as_session(self, primitive: type, registry: BaseRegistry) -> None:
        """Test initializing a primitive with mode as Session."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Session(backend)

        inst = primitive(mode=session)
        assert inst.mode is not None
        inst.run(**get_primitive_inputs(inst, backend=backend))
        assert inst.mode == session
        assert session._backend == backend

    @pytest.mark.parametrize("primitive", [SamplerV2, EstimatorV2])
    def test_init_with_mode_as_batch(self, primitive: type, registry: BaseRegistry) -> None:
        """Test initializing a primitive with mode as a Batch."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        batch = Batch(backend)

        inst = primitive(mode=batch)
        assert inst.mode is not None
        inst.run(**get_primitive_inputs(inst, backend=backend))
        assert batch._backend == backend

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_parameters_single_circuit(self, primitive: type) -> None:
        """Test parameters for a single circuit."""
        circ = real_amplitudes(num_qubits=2, reps=1)
        circ.measure_all()
        backend = FakeVigoV2()
        circ = transpile(circ, backend=backend)

        param_vals = [
            # 1 set of parameter values
            [1, 2, 3, 4],
            [np.pi] * circ.num_parameters,
            np.random.uniform(size=(4,)),
            {param: [2.0] for param in circ.parameters},
            # N sets of parameter values
            [[1, 2, 3, 4]] * 2,
            np.random.random((2, 4)),
            np.linspace(0, 1, 24).reshape((2, 3, 4)),
            {param: [1, 2, 3] for param in circ.parameters},
            {param: np.linspace(0, 1, 5) for param in circ.parameters},
            {tuple(circ.parameters): np.random.random((2, 3, 4))},
            {
                tuple(circ.parameters[:2]): np.random.random((2, 1, 2)),
                tuple(circ.parameters[2:4]): np.random.random((2, 1, 2)),
            },
        ]

        inst = primitive(mode=backend)
        for val in param_vals:
            pub = (circ, "ZZIII", val) if isinstance(inst, EstimatorV2) else (circ, val)
            inst.run([pub])

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_nd_parameters_0d(self, primitive: type) -> None:
        """Test with 0-dimensional parameters."""
        circ = real_amplitudes(num_qubits=2, reps=1)
        circ.measure_all()
        backend = FakeVigoV2()
        circ = transpile(circ, backend=backend)
        inst = primitive(mode=backend)

        barray = {tuple(circ.parameters): np.linspace(0, 1, 4)}
        pub = (circ, "ZZIII", barray) if isinstance(inst, EstimatorV2) else (circ, barray)
        inst.run([pub])

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_nd_parameters_nd(self, primitive: type) -> None:
        """Test with n-dimensional parameters."""
        circ = real_amplitudes(num_qubits=2, reps=1)
        circ.measure_all()
        backend = FakeVigoV2()
        circ = transpile(circ, backend=backend)
        inst = primitive(mode=backend)

        barray = {tuple(circ.parameters): np.random.random((2, 3, 4))}
        pub = (circ, "ZZIII", barray) if isinstance(inst, EstimatorV2) else (circ, barray)
        inst.run([pub])

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize(
        "all_params",
        [
            (
                [],
                np.random.uniform(size=(4,)),
                np.random.uniform(size=(6,)),
            ),
            (
                [],
                np.random.random((2, 4)),
                np.random.random((2, 6)),
            ),
        ],
    )
    def test_parameters_multiple_circuits(self, primitive: type, all_params: tuple) -> None:
        """Test multiple parameters for multiple circuits."""
        backend = FakeVigoV2()
        qc2 = QuantumCircuit(2)
        qc2.measure_all()
        ra2 = real_amplitudes(num_qubits=2, reps=1)
        ra2.measure_all()
        ra3 = real_amplitudes(num_qubits=3, reps=1)
        ra3.measure_all()
        circuits = [
            transpile(qc2, backend=backend),
            transpile(ra2, backend=backend),
            transpile(ra3, backend=backend),
        ]

        inst = primitive(mode=backend)
        pubs: list = []
        for circ, circ_params in zip(circuits, all_params):
            publet = (
                (circ, "Z" * backend.num_qubits, circ_params)
                if isinstance(inst, EstimatorV2)
                else (circ, circ_params)
            )
            pubs.append(publet)
        inst.run(pubs)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize(
        "options",
        [
            {"dynamical_decoupling": {"sequence_type": "XY4"}},
            {"default_shots": 2000},
            {"execution": {"init_qubits": True}},
        ],
    )
    def test_run_updated_options(
        self, primitive: type[EstimatorV2 | SamplerV2], options: dict
    ) -> None:
        """Test run using overwritten options."""
        opts = primitive._options_class()
        opts.update(**options)
        inputs = primitive._options_class._get_program_inputs(asdict(opts))["options"]
        assert_dict_partially_equal(inputs, options)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize(
        ("options", "expected"),
        [
            ({"environment": {"log_level": "DEBUG"}}, {"log_level": "DEBUG"}),
            ({"environment": {"job_tags": ["foo", "bar"]}}, {"job_tags": ["foo", "bar"]}),
            ({"max_execution_time": 600}, {"max_execution_time": 600}),
            (
                {"environment": {"log_level": "INFO"}, "max_execution_time": 800},
                {"log_level": "INFO", "max_execution_time": 800},
            ),
        ],
    )
    def test_run_overwrite_runtime_options(
        self, primitive: type[EstimatorV2 | SamplerV2], options: dict, expected: dict
    ) -> None:
        """Test run using overwritten runtime options."""
        opts = primitive._options_class()
        opts.update(**options)
        rt_options = primitive._options_class._get_runtime_options(asdict(opts))
        assert_dict_partially_equal(rt_options, expected)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize("exp_opt", [{"foo": "bar", "execution": {"extra_key": "bar"}}])
    def test_run_experimental_options(
        self, primitive: type[EstimatorV2 | SamplerV2], exp_opt: dict
    ) -> None:
        """Test specifying arbitrary options in run."""
        opts = primitive._options_class()
        opts.experimental = exp_opt
        inputs = primitive._options_class._get_program_inputs(asdict(opts))["options"]
        assert inputs["experimental"] == {"foo": "bar"}
        assert inputs["execution"] == {"extra_key": "bar"}
        assert "extra_key" not in inputs

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize("exp_opt", [{"foo": "bar", "execution": {"extra_key": "bar"}}])
    def test_run_experimental_options_init(
        self, primitive: type[EstimatorV2 | SamplerV2], exp_opt: dict
    ) -> None:
        """Test specifying arbitrary options in initialization."""
        opts = primitive._options_class(experimental=exp_opt)  # type: ignore[call-arg]
        inputs = primitive._options_class._get_program_inputs(asdict(opts))["options"]
        assert inputs["experimental"] == {"foo": "bar"}
        assert inputs["execution"] == {"extra_key": "bar"}
        assert "extra_key" not in inputs

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_run_unset_options(self, primitive: type[EstimatorV2 | SamplerV2]) -> None:
        """Test running with unset options."""
        opts = primitive._options_class()
        inputs = primitive._options_class._get_program_inputs(asdict(opts))["options"]
        assert not inputs

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_run_multiple_different_options(
        self, primitive: type, registry: BaseRegistry, responses: RequestsMock
    ) -> None:
        """Test multiple runs with different options."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        inst = primitive(mode=backend, options={"default_shots": 100})
        inst.run(**get_primitive_inputs(inst, backend=backend))
        inst.options.update(default_shots=200)
        inst.run(**get_primitive_inputs(inst, backend=backend))

        jobs = get_submitted_jobs(responses)
        assert [job["params"]["options"]["default_shots"] for job in jobs] == [100, 200]

    def test_run_same_session(self, registry: BaseRegistry) -> None:
        """Test multiple runs within a session."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Session(backend)

        num_runs = 5
        primitives: list[type[EstimatorV2 | SamplerV2]] = [EstimatorV2, SamplerV2]

        jobs: list = []
        for idx in range(num_runs):
            cls = primitives[idx % len(primitives)]
            inst = cls(mode=session)
            jobs.append(inst.run(**get_primitive_inputs(inst)))

        assert len(jobs) == 5
        assert all(job.session_id == "session_12345" for job in jobs)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize(
        "new_opts",
        [
            {"default_shots": 200},
            {"dynamical_decoupling": {"enable": True}, "default_shots": 300},
        ],
    )
    def test_set_options(self, primitive: type, new_opts: dict) -> None:
        """Test set options."""
        opt_cls = primitive._options_class  # type: ignore[attr-defined]
        options = opt_cls(default_shots=100)
        backend = FakeVigoV2()

        inst = primitive(mode=backend, options=options)
        inst.options.update(**new_opts)
        # Make sure the values are equal.
        inst_options = asdict(inst.options)
        assert_dict_flat_partially_equal(inst_options, new_opts)
        # Make sure the structure didn't change.
        assert_dict_keys_equal(inst_options, asdict(opt_cls()))

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_raise_faulty_qubits(self, primitive: type) -> None:
        """Test faulty qubits is raised."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ.x(i)
        transpiled = transpile(circ, backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        inst = primitive(mode=ibm_backend)

        if isinstance(inst, IBMBaseEstimator):
            pub: tuple = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with pytest.raises(ValueError) as err:
            inst.run(pubs=[pub])
        assert f"faulty qubit {faulty_qubit}" in str(err.value)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_raise_faulty_qubits_many(self, primitive: type) -> None:
        """Test faulty qubits is raised if one circuit uses it."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits

        circ1 = QuantumCircuit(1, 1)
        circ1.x(0)
        circ2 = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ2.x(i)
        transpiled = transpile([circ1, circ2], backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)

        inst = primitive(ibm_backend)
        if isinstance(inst, IBMBaseEstimator):
            pubs: list = [(transpiled[0], observable), (transpiled[1], observable)]
        else:
            for circ in transpiled:
                circ.measure_all()
            pubs = [(transpiled[0],), (transpiled[1],)]

        with pytest.raises(ValueError) as err:
            inst.run(pubs=pubs)
        assert f"faulty qubit {faulty_qubit}" in str(err.value)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_raise_faulty_edge(self, primitive: type) -> None:
        """Test faulty edge is raised."""
        fake_backend = FakeManilaV2()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits - 2):
            circ.cx(i, i + 1)
        transpiled = transpile(circ, backend=fake_backend, optimization_level=1)
        observable = SparsePauliOp("Z" * num_qubits)

        edge_qubits = [0, 1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))

        inst = primitive(ibm_backend)
        if isinstance(inst, IBMBaseEstimator):
            pub: tuple = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with pytest.raises(ValueError) as err:
            inst.run(pubs=[pub])
        assert "cx" in str(err.value)
        assert f"faulty edge {tuple(edge_qubits)}" in str(err.value)

    def test_faulty_qubit_not_used(self) -> None:
        """Test faulty qubit is not raise if not used."""
        fake_backend = FakeManilaV2()
        circ = QuantumCircuit(2, 2)
        for i in range(2):
            circ.x(i)
        transpiled = transpile(circ, backend=fake_backend, initial_layout=[0, 1])

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)

        # A circuit that does not use the faulty qubit is accepted.
        ibm_backend.check_faulty(transpiled)

    def test_faulty_edge_not_used(self) -> None:
        """Test faulty edge is not raised if not used."""
        fake_backend = FakeManilaV2()
        coupling_map = fake_backend.configuration().coupling_map

        circ = QuantumCircuit(2, 2)
        circ.cx(0, 1)

        transpiled = transpile(circ, backend=fake_backend, initial_layout=coupling_map[0])
        edge_qubits = coupling_map[-1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))

        # A circuit that does not use the faulty edge is accepted.
        ibm_backend.check_faulty(transpiled)

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_abstract_circuits(self, primitive: type) -> None:
        """Test passing in abstract circuit would fail."""
        inst = primitive(mode=FakeVigoV2())
        circ = QuantumCircuit(3, 3)
        circ.cx(0, 2)
        pub = [circ]
        if isinstance(inst, EstimatorV2):
            pub.append(SparsePauliOp("ZZZ"))
        else:
            circ.measure_all()

        with pytest.raises(IBMInputValueError, match="target hardware"):
            inst.run(pubs=[tuple(pub)])

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    def test_get_backend_primitive(self, primitive: type) -> None:
        """Test getting the backend used in the primitive."""
        backend = FakeVigoV2()
        inst = primitive(mode=backend)
        assert inst.backend().name == backend.name

    @pytest.mark.parametrize("primitive", [EstimatorV2, SamplerV2])
    @pytest.mark.parametrize("session", [Session, Batch])
    def test_get_backend_session(self, primitive: type, session: type) -> None:
        """Test getting the backend used in the primitive when session is used."""
        backend = FakeManilaV2()
        with session(backend=backend):
            inst = primitive()
            assert inst.backend().name == backend.name


class TestGetModeServiceBackend:
    """Test the function ``get_mode_service_backend``."""

    def test_mode_is_backend(self, registry: BaseRegistry) -> None:
        """Test ``get_mode_service_backend`` when the input mode is an ``IBMBackend``."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        result = get_mode_service_backend(mode=backend)
        assert result[0] is None
        assert result[1] == backend.service
        assert result[2] == backend

    def test_mode_is_session(self, registry: BaseRegistry) -> None:
        """Test ``get_mode_service_backend`` when the input mode is a session."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Session(backend)

        result = get_mode_service_backend(mode=session)
        assert result[0] == session
        assert result[1] == session.service
        assert result[2].name == "common_backend"

    def test_session_context_manager(self, registry: BaseRegistry) -> None:
        """Test ``get_mode_service_backend`` inside a session context manager."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        with Session(backend=backend) as session:
            result = get_mode_service_backend()
            assert result[0] == session
            assert result[1] == backend.service
            assert result[2] == backend

    def test_mode_is_backend_inside_session_context_manager(self, registry: BaseRegistry) -> None:
        """Test ``get_mode_service_backend`` inside a session context manager (IBMBackend mode).

        Test ``get_mode_service_backend`` inside a session context manager,
        when the input mode is an ``IBMBackend``.
        """
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        with Session(backend=backend) as session:
            result = get_mode_service_backend(mode=backend)
            assert result[0] == session
            assert result[1] == backend.service
            assert result[2] == backend
