# This code is part of Qiskit.
#
# (C) Copyright IBM 2023-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Sampler V2."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from ddt import data, ddt, named_data
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import UnitaryGate, real_amplitudes
from qiskit.primitives import PrimitiveResult, PubResult
from qiskit.primitives.containers import BitArray
from qiskit.primitives.containers.data_bin import DataBin
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime.exceptions import RuntimeJobFailureError
from qiskit_ibm_runtime.fake_provider import FakeManilaV2

from .case import IBMIntegrationTestCase

if TYPE_CHECKING:
    from qiskit_ibm_runtime import IBMBackend


SHOTS = 10000

# TODO: Re-add seed_simulator and re-enable verification once it's supported
# OPTIONS = {"default_shots": SHOTS, "seed_simulator": 123}
OPTIONS = {"default_shots": SHOTS}


def bell_circuit() -> QuantumCircuit:
    """Return a two-qubit bell circuit, with all its qubits measured."""
    bell = QuantumCircuit(2, name="Bell")
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()

    return bell


def sampler_cases() -> list[tuple]:
    """Return the circuit, parameter values, and expected counts of seven sampler cases."""
    fake_backend = FakeManilaV2()

    hadamard = QuantumCircuit(1, 1, name="Hadamard")
    hadamard.h(0)
    hadamard.measure(0, 0)

    pqc = real_amplitudes(num_qubits=2, reps=2)
    pqc.measure_all()
    pqc = transpile(circuits=pqc, backend=fake_backend)

    pqc2 = real_amplitudes(num_qubits=2, reps=3)
    pqc2.measure_all()
    pqc2 = transpile(circuits=pqc2, backend=fake_backend)

    return [
        (hadamard, None, {0: 5000, 1: 5000}),
        (bell_circuit(), None, {0: 5000, 3: 5000}),
        (pqc, [0] * 6, {0: 10000}),
        (pqc, [1] * 6, {0: 168, 1: 3389, 2: 470, 3: 5973}),
        (pqc, [0, 1, 1, 2, 3, 5], {0: 1339, 1: 3534, 2: 912, 3: 4215}),
        (pqc, [1, 2, 3, 4, 5, 6], {0: 634, 1: 291, 2: 6039, 3: 3036}),
        (pqc2, [0, 1, 2, 3, 4, 5, 6, 7], {0: 1898, 1: 6864, 2: 928, 3: 311}),
    ]


def multiple_cregs_cases() -> list[tuple]:
    """Return the title, circuit and expected counts of the multiple classical register cases."""
    cases = []

    # Use all cregs.
    a = ClassicalRegister(1, "a")
    b = ClassicalRegister(2, "b")
    c = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(QuantumRegister(3), a, b, c)
    circuit.h(range(3))
    circuit.measure([0, 1, 2, 2], [0, 2, 4, 5])
    target = {"a": {0: 5000, 1: 5000}, "b": {0: 5000, 2: 5000}, "c": {0: 5000, 6: 5000}}
    cases.append(("use all cregs", circuit, target))

    # Use only a and b, with a wider b.
    a = ClassicalRegister(1, "a")
    b = ClassicalRegister(5, "b")
    c = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(QuantumRegister(3), a, b, c)
    circuit.h(range(3))
    circuit.measure([0, 1, 2, 2], [0, 2, 4, 5])
    target = {
        "a": {0: 5000, 1: 5000},
        "b": {0: 2500, 2: 2500, 24: 2500, 26: 2500},
        "c": {0: 10000},
    }
    cases.append(("use only a and b", circuit, target))

    # Use only c.
    a = ClassicalRegister(1, "a")
    b = ClassicalRegister(2, "b")
    c = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(QuantumRegister(3), a, b, c)
    circuit.h(range(3))
    circuit.measure(1, 5)
    target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 5000, 4: 5000}}
    cases.append(("use only c", circuit, target))

    # Use only c, measuring multiple qubits into the same clbit.
    a = ClassicalRegister(1, "a")
    b = ClassicalRegister(2, "b")
    c = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(QuantumRegister(3), a, b, c)
    circuit.h(range(3))
    circuit.measure([0, 1, 2], [5, 5, 5])
    target = {"a": {0: 10000}, "b": {0: 10000}, "c": {0: 5000, 4: 5000}}
    cases.append(("use only c multiple qubits", circuit, target))

    return cases


def isa_bell_circuit(backend: IBMBackend) -> QuantumCircuit:
    """Return a bell circuit transpiled for `backend`."""
    pass_manager = generate_preset_pass_manager(optimization_level=1, target=backend.target)

    return pass_manager.run(bell_circuit())


def assert_result_type(result, num_pubs, targets=None):
    """Assert result type."""
    assert isinstance(result, PrimitiveResult)
    assert isinstance(result.metadata, dict)
    assert len(result) == num_pubs
    for idx, pub_result in enumerate(result):
        # TODO: We need to update the following test to check `SamplerPubResult`
        # when the server side is upgraded to Qiskit 1.1.
        assert isinstance(pub_result, PubResult)
        assert isinstance(pub_result.data, DataBin)
        assert isinstance(pub_result.metadata, dict)
        if targets:
            assert isinstance(result[idx].data.meas, BitArray)


@ddt
class TestSampler(IBMIntegrationTestCase):
    """Test Sampler."""

    @named_data(
        # The parameter values to be paired with the circuit in the pub, if any.
        ("single", None),
        ("single_with_param", ()),
        ("single_array", [()]),
        ("multiple", [(), (), ()]),
    )
    def test_sampler_run(self, parameter_values):
        """Test Sampler.run()."""
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)
        _, _, target = sampler_cases()[1]
        pub = isa_bell if parameter_values is None else (isa_bell, parameter_values)

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            job = sampler.run([pub])
            result = job.result()

        assert_result_type(result, num_pubs=1, targets=[np.array(target)])

    def test_sample_run_multiple_circuits(self):
        """Test Sampler.run() with multiple circuits."""
        backend = self.service.backend(self.dependencies.qpu)
        cases = sampler_cases()
        isa_bell = isa_bell_circuit(backend)

        _, _, target = cases[1]
        sampler = Sampler(mode=backend, options=OPTIONS)
        result = sampler.run([isa_bell, isa_bell, isa_bell]).result()
        assert_result_type(result, num_pubs=3, targets=[np.array(target)] * 3)

    def test_sampler_run_with_parameterized_circuits(self):
        """Test Sampler.run() with parameterized circuits."""
        cases = sampler_cases()

        pqc1, param1, target1 = cases[4]
        pqc2, param2, target2 = cases[5]
        pqc3, param3, target3 = cases[6]

        sampler = Sampler(mode=FakeManilaV2(), options=OPTIONS)
        result = sampler.run([(pqc1, param1), (pqc2, param2), (pqc3, param3)]).result()
        assert_result_type(
            result, num_pubs=3, targets=[np.array(target1), np.array(target2), np.array(target3)]
        )

    def test_run_1qubit(self):
        """Test for 1-qubit cases."""
        backend = self.service.backend(self.dependencies.qpu)

        qc = QuantumCircuit(1)
        qc.measure_all()
        qc2 = QuantumCircuit(1)
        qc2.x(0)
        qc2.measure_all()

        sampler = Sampler(mode=backend, options=OPTIONS)
        result = sampler.run([qc, qc2]).result()
        assert_result_type(result, num_pubs=2)

    def test_run_2qubit(self):
        """Test for 2-qubit cases."""
        backend = self.service.backend(self.dependencies.qpu)

        qc0 = QuantumCircuit(2)
        qc0.measure_all()
        qc1 = QuantumCircuit(2)
        qc1.x(0)
        qc1.measure_all()
        qc2 = QuantumCircuit(2)
        qc2.x(1)
        qc2.measure_all()
        qc3 = QuantumCircuit(2)
        qc3.x([0, 1])
        qc3.measure_all()

        sampler = Sampler(mode=backend, options=OPTIONS)
        result = sampler.run([qc0, qc1, qc2, qc3]).result()
        assert_result_type(result, num_pubs=4)

    @named_data(
        # The empty parameter values accepted by a circuit that takes no parameters.
        ("none", None),
        ("empty_tuple", ()),
        ("empty_list", []),
        ("empty_array", np.array([])),
        ("tuple_of_empty_tuple", ((),)),
        ("tuple_of_empty_list", ([],)),
        ("list_of_empty_list", [[]]),
        ("list_of_empty_tuple", [()]),
        ("array_of_empty_array", np.array([[]])),
    )
    def test_run_single_circuit_no_parameter(self, parameter_values):
        """Test for single circuit case, for a circuit without parameters."""
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)
        _, _, target = sampler_cases()[1]

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            result = sampler.run([(isa_bell, parameter_values)]).result()

        assert_result_type(result, num_pubs=1, targets=[np.array(target)])

    @named_data(
        # The shapes accepted for the values of a circuit that takes a single parameter.
        ("list", [np.pi]),
        ("tuple", (np.pi,)),
        ("array", np.array([np.pi])),
        ("nested_list", [[np.pi]]),
        ("nested_tuple", ((np.pi,),)),
        ("nested_array", np.array([[np.pi]])),
    )
    def test_run_single_circuit_one_parameter(self, parameter_values):
        """Test for single circuit case, for a circuit with a single parameter."""
        backend = self.service.backend(self.dependencies.qpu)
        pass_manager = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        circuit = QuantumCircuit(1, 1, name="X gate")
        circuit.ry(Parameter("x"), 0)
        circuit.measure(0, 0)

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            result = sampler.run([(pass_manager.run(circuit), parameter_values)]).result()

        assert_result_type(result, num_pubs=1)

    @named_data(
        # The shapes accepted for the values of a circuit that takes more than one parameter.
        # The values match the ones of `sampler_cases()[3]`, used by the test.
        ("list", [1] * 6),
        ("tuple", (1,) * 6),
        ("array", np.array([1] * 6)),
        ("nested_list", [[1] * 6]),
        ("nested_tuple", ([1] * 6,)),
        ("nested_array", np.array([[1] * 6])),
    )
    def test_run_single_circuit_more_than_one_parameter(self, parameter_values):
        """Test for single circuit case, for a circuit with more than one parameter."""
        backend = self.service.backend(self.dependencies.qpu)
        circuit, _, target = sampler_cases()[3]
        pass_manager = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            result = sampler.run([(pass_manager.run(circuit), parameter_values)]).result()

        assert_result_type(result, num_pubs=1, targets=[np.array(target)])

    def test_run_reverse_meas_order(self):
        """Test for sampler with reverse measurement order."""
        backend = self.service.backend(self.dependencies.qpu)

        x = Parameter("x")
        y = Parameter("y")

        qc = QuantumCircuit(3, 3)
        qc.rx(x, 0)
        qc.rx(y, 1)
        qc.x(2)
        qc.measure(0, 2)
        qc.measure(1, 1)
        qc.measure(2, 0)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        sampler = Sampler(mode=backend, options=OPTIONS)
        result = sampler.run([(pm.run(qc), [0, 0]), (pm.run(qc), [np.pi / 2, 0])]).result()
        assert_result_type(result, num_pubs=2)

    @data(1, 2)
    def test_run_empty_parameter(self, num_circuits):
        """Test for empty parameter."""
        backend = self.service.backend(self.dependencies.qpu)

        n = 5
        qc = QuantumCircuit(n, n - 1)
        qc.measure(range(n - 1), range(n - 1))

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            result = sampler.run([qc] * num_circuits).result()

        assert_result_type(result, num_pubs=num_circuits)

    @data("ndarray", "list")
    def test_run_numpy_params(self, params_type):
        """Test for numpy array as parameter values."""
        backend = self.service.backend(self.dependencies.qpu)

        qc = real_amplitudes(num_qubits=2, reps=2)
        qc.measure_all()
        qc = transpile(circuits=qc, backend=backend)
        k = 5
        params_array = np.random.rand(k, qc.num_parameters)
        params_list = params_array.tolist()

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            target = sampler.run([(qc, params_list)]).result()

            if params_type == "ndarray":
                result = sampler.run([(qc, params_array)]).result()
                num_pubs = 1
            else:
                result = sampler.run([(qc, params) for params in params_list]).result()
                num_pubs = len(params_list)

        assert_result_type(result, num_pubs=num_pubs, targets=[np.array(target)])

    def test_run_with_shots_option_init_option(self):
        """Test with the number of shots set in the options the sampler is created with."""
        shots = 100
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)

        with Session(backend) as session:
            sampler = Sampler(mode=session, options={"default_shots": shots})
            result = sampler.run([isa_bell]).result()

        assert result[0].data.meas.num_shots == shots
        assert sum(result[0].data.meas.get_counts().values()) == shots
        assert_result_type(result, num_pubs=1)

    def test_run_with_shots_option_update_option(self):
        """Test with the number of shots set in the options of an existing sampler."""
        shots = 100
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)

        with Session(backend) as session:
            sampler = Sampler(mode=session)
            sampler.options.default_shots = shots
            result = sampler.run([isa_bell]).result()

        assert result[0].data.meas.num_shots == shots
        assert sum(result[0].data.meas.get_counts().values()) == shots
        assert_result_type(result, num_pubs=1)

    def test_run_with_shots_option_run_arg(self):
        """Test with the number of shots set as an argument of `Sampler.run()`."""
        shots = 100
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)

        with Session(backend) as session:
            sampler = Sampler(mode=session)
            result = sampler.run(pubs=[isa_bell], shots=shots).result()

        assert result[0].data.meas.num_shots == shots
        assert sum(result[0].data.meas.get_counts().values()) == shots
        assert_result_type(result, num_pubs=1)

    def test_run_with_shots_option_pub_like(self):
        """Test with the number of shots set in a pub-like tuple."""
        shots = 100
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)

        with Session(backend) as session:
            sampler = Sampler(mode=session)
            result = sampler.run([(isa_bell, None, shots)]).result()

        assert result[0].data.meas.num_shots == shots
        assert sum(result[0].data.meas.get_counts().values()) == shots
        assert_result_type(result, num_pubs=1)

    def test_run_with_shots_option_pub(self):
        """Test with the number of shots set in a `SamplerPub`."""
        shots = 100
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)

        with Session(backend) as session:
            sampler = Sampler(mode=session)
            result = sampler.run([SamplerPub(isa_bell, shots=shots)]).result()

        assert result[0].data.meas.num_shots == shots
        assert sum(result[0].data.meas.get_counts().values()) == shots
        assert_result_type(result, num_pubs=1)

    def test_run_with_shots_option_multiple_pubs(self):
        """Test with per-pub shots option."""
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)

        shots1 = 100
        shots2 = 200
        sampler = Sampler(mode=backend)
        result = sampler.run(
            [
                SamplerPub(isa_bell, shots=shots1),
                SamplerPub(isa_bell, shots=shots2),
            ]
        ).result()
        assert result[0].data.meas.num_shots == shots1
        assert sum(result[0].data.meas.get_counts().values()) == shots1
        assert result[1].data.meas.num_shots == shots2
        assert sum(result[1].data.meas.get_counts().values()) == shots2
        assert_result_type(result, num_pubs=2)

    def test_run_shots_result_size(self):
        """Test with shots option to validate the result size."""
        backend = self.service.backend(self.dependencies.qpu)

        n = 10
        qc = QuantumCircuit(n)
        qc.h(range(n))
        qc.measure_all()
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        sampler = Sampler(mode=backend, options=OPTIONS)
        result = sampler.run([pm.run(qc)]).result()
        assert result[0].data.meas.num_shots <= SHOTS
        assert sum(result[0].data.meas.get_counts().values()) == SHOTS
        assert_result_type(result, num_pubs=1)

    def test_primitive_job_status_done(self):
        """Test primitive job's status."""
        backend = self.service.backend(self.dependencies.qpu)
        isa_bell = isa_bell_circuit(backend)

        sampler = Sampler(mode=backend, options=OPTIONS)
        job = sampler.run([isa_bell])
        _ = job.result()
        assert job.status() == "DONE"

    @named_data(
        ("identity", UnitaryGate(np.eye(2))),
        ("X", UnitaryGate([[0, 1], [1, 0]])),
    )
    def test_circuit_with_unitary(self, gate):
        """Test for circuit with unitary gate."""
        backend = self.service.backend(self.dependencies.qpu)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        circuit = QuantumCircuit(1)
        circuit.append(gate, [0])
        circuit.measure_all()

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            result = sampler.run([pm.run(circuit)]).result()

        assert_result_type(result, num_pubs=1)

    def test_metadata(self):
        """Test for metatdata."""
        backend = self.service.backend(self.dependencies.qpu)
        cases = sampler_cases()

        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        qc, _, _ = cases[1]
        sampler = Sampler(mode=backend, options=OPTIONS)
        result = sampler.run([pm.run(qc)]).result()
        assert result[0].data.meas.num_shots == SHOTS
        assert_result_type(result, num_pubs=1)

    @named_data(*multiple_cregs_cases())
    def test_circuit_with_multiple_cregs(self, circuit, target):
        """Test for circuit with multiple classical registers."""
        backend = self.service.backend(self.dependencies.qpu)
        pass_manager = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        with Session(backend) as session:
            sampler = Sampler(mode=session, options=OPTIONS)
            result = sampler.run([pass_manager.run(circuit)]).result()

        assert len(result[0].data) == len(target)
        assert_result_type(result, num_pubs=1)

    def test_sampler_v2_options(self):
        """Test SamplerV2 options."""
        backend = self.service.backend(self.dependencies.qpu)
        cases = sampler_cases()
        isa_bell = isa_bell_circuit(backend)

        sampler = Sampler(mode=backend)
        sampler.options.default_shots = 4096
        sampler.options.execution.init_qubits = True
        sampler.options.execution.rep_delay = 0.00025

        _, _, target = cases[1]
        job = sampler.run([isa_bell])
        result = job.result()
        assert_result_type(result, num_pubs=1, targets=[np.array(target)])

    def test_sampler_v2_dd(self):
        """Test SamplerV2 DD options."""
        backend = self.service.backend(self.dependencies.qpu)
        cases = sampler_cases()

        sampler = Sampler(mode=backend)
        sampler.options.dynamical_decoupling.enable = True
        sampler.options.dynamical_decoupling.sequence_type = "XX"
        sampler.options.dynamical_decoupling.extra_slack_distribution = "middle"
        sampler.options.dynamical_decoupling.scheduling_method = "asap"
        sampler.options.dynamical_decoupling.skip_reset_qubits = True
        bell, _, _ = cases[1]
        bell = transpile(bell, backend)
        job = sampler.run([bell])
        try:
            result = job.result()
        except RuntimeJobFailureError as ex:
            if "Error code 6050" in ex.message:
                self.skipTest("Backend cannot be used for this test")
        assert_result_type(result, num_pubs=1)
