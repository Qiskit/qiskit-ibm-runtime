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

"""General utility functions for testing."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest import mock

import numpy as np
from qiskit.circuit import ClassicalRegister, Parameter, QuantumCircuit, QuantumRegister
from qiskit.compiler import transpile
from qiskit.quantum_info import Pauli, SparsePauliOp

from qiskit_ibm_runtime import EstimatorV2, QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.models import BackendConfiguration, BackendProperties, BackendStatus

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.providers.backend import Backend, BackendV2


def create_faulty_backend(
    model_backend: Backend,
    faulty_qubit: int | None = None,
    faulty_edge: tuple | None = None,
    faulty_q1_property: int | None = None,
) -> IBMBackend:
    """Create an IBMBackend that has faulty qubits and/or edges.

    Args:
        model_backend: Fake backend to model after.
        faulty_qubit: Faulty qubit.
        faulty_edge: Faulty edge, a tuple of (gate, qubits)
        faulty_q1_property: Faulty Q1 property.

    Returns:
        An IBMBackend with faulty qubits/edges.
    """
    properties = model_backend.properties().to_dict()

    if faulty_qubit:
        properties["qubits"][faulty_qubit].append(
            {"date": datetime.now(), "name": "operational", "unit": "", "value": 0}
        )

    if faulty_edge:
        gate, qubits = faulty_edge
        for gate_obj in properties["gates"]:
            if gate_obj["gate"] == gate and gate_obj["qubits"] == qubits:
                gate_obj["parameters"].append(
                    {
                        "date": datetime.now(),
                        "name": "operational",
                        "unit": "",
                        "value": 0,
                    }
                )

    if faulty_q1_property:
        properties["qubits"][faulty_q1_property] = [
            q for q in properties["qubits"][faulty_q1_property] if q["name"] != "T1"
        ]

    out_backend = IBMBackend(
        configuration=model_backend.configuration(),
        service=mock.MagicMock(),
        api_client=None,
        instance=None,
    )

    out_backend.status = lambda: BackendStatus(  # type: ignore[assignment]
        backend_name="foo",
        backend_version="1.0",
        operational=True,
        pending_jobs=0,
        status_msg="",
    )
    out_backend.properties = lambda: BackendProperties.from_dict(properties)  # type: ignore
    return out_backend


def get_mocked_backend(
    name: str = "ibm_gotham",
    configuration: dict | None = None,
    properties: dict | None = None,
) -> IBMBackend:
    """Return a mock backend."""
    mock_service = mock.MagicMock(spec=QiskitRuntimeService, is_local=False)
    mock_api_client = mock.MagicMock()
    mock_api_client._instance = "mock_instance"
    mock_service._active_api_client = mock_api_client

    configuration = (
        FakeManilaV2().configuration()  # type: ignore[assignment]
        if configuration is None
        else BackendConfiguration.from_dict(configuration)
    )

    mock_api_client.backend_properties = lambda *args, **kwargs: properties
    mock_api_client.session_details = mock.MagicMock(return_value={"mode": "dedicated"})
    mock_backend = IBMBackend(
        configuration=configuration,  # type: ignore[arg-type]
        service=mock_service,
        api_client=mock_api_client,
    )
    mock_backend.name = name
    mock_backend._instance = None
    mock_service.backend = lambda name, **kwargs: (
        mock_backend if name == mock_backend.name else None
    )
    mock_service._get_api_client = mock.MagicMock(return_value=mock_api_client)

    return mock_backend


def bell() -> QuantumCircuit:
    """Return a Bell circuit."""
    quantum_register = QuantumRegister(2, name="qr")
    classical_register = ClassicalRegister(2, name="cr")
    quantum_circuit = QuantumCircuit(quantum_register, classical_register, name="bell")
    quantum_circuit.h(quantum_register[0])
    quantum_circuit.cx(quantum_register[0], quantum_register[1])
    quantum_circuit.measure(quantum_register, classical_register)

    return quantum_circuit


def make_mirror_circuit_with_phases(
    backend: BackendV2,
    num_qubits: int = 2,
    layers: int = 4,
    *,
    seed: int | None = 7,
    add_measurement: bool = True,
    add_rx: bool = True,
) -> QuantumCircuit:
    """Make a circuit that composes a mirror circuit with a final layer of RX gates.

    The mirror circuit contains entanglers between nearest neighbours.
    """
    if "cz" in (basis_gates := backend.configuration().basis_gates):
        entangler = "cz"
    elif "cx" in basis_gates:
        entangler = "cx"
    elif "ecr" in basis_gates:
        entangler = "ecr"
    else:
        # This should not be reachable
        raise ValueError("No entangler found.")

    even_pairs = zip(range(0, backend.num_qubits, 2), range(1, backend.num_qubits, 2))
    layer1_pairs = [
        (control, target)
        for control, target in even_pairs
        if backend.target.instruction_supported(entangler, (control, target))
        and control < num_qubits
        and target < num_qubits
    ]
    layer1 = QuantumCircuit(num_qubits)
    for control, target in layer1_pairs:
        getattr(layer1, entangler)(control, target)

    odd_pairs = zip(range(1, backend.num_qubits, 2), range(2, backend.num_qubits, 2))
    layer2_pairs = [
        (control, target)
        for control, target in odd_pairs
        if backend.target.instruction_supported(entangler, (control, target))
        and control < num_qubits
        and target < num_qubits
    ]
    layer2 = QuantumCircuit(num_qubits)
    for control, target in layer2_pairs:
        getattr(layer2, entangler)(control, target)

    rng = np.random.default_rng(seed)
    mirror = QuantumCircuit(num_qubits)
    for _ in range(layers):
        mirror.compose(layer1, inplace=True)
        mirror.rx(rng.uniform(0, 2 * np.pi), range(num_qubits))
        mirror.compose(layer2, inplace=True)
        mirror.rx(rng.uniform(0, 2 * np.pi), range(num_qubits))

    circuit = QuantumCircuit(num_qubits)
    circuit.compose(mirror, inplace=True)
    circuit.barrier()  # keep U and U† from resolving to identity under transpilation
    circuit.compose(mirror.inverse(), inplace=True)

    circuit.barrier()
    if add_rx:
        for qubit in range(num_qubits):
            circuit.rx(Parameter(f"theta_{qubit}"), qubit)
    if add_measurement:
        circuit.measure_all()
    return circuit


def get_transpiled_circuit(
    backend: IBMBackend, num_qubits: int = 2, measure: bool = False
) -> QuantumCircuit:
    """Return a transpiled circuit."""
    circ = QuantumCircuit(num_qubits)
    circ.h(0)
    for idx in range(num_qubits - 2):
        circ.cx(idx, idx + 1)
    if measure:
        circ.measure_all()
    return transpile(circ, backend=backend)


def get_primitive_inputs(
    primitive: type, backend: BackendV2 | None = None, num_sets: int = 1
) -> dict:
    """Return primitive specific inputs."""
    backend = backend or FakeManilaV2()
    theta = Parameter("θ")
    circ = QuantumCircuit(2)
    circ.h(0)
    circ.cx(0, 1)
    circ.ry(theta, 0)

    circ = transpile(circ, backend=backend)
    obs = SparsePauliOp.from_list([("IZ", 1)])
    obs = obs.apply_layout(circ.layout, num_qubits=circ.num_qubits)
    param_val = [0.1]

    if isinstance(primitive, EstimatorV2):
        return {"pubs": [(circ, [obs], [param_val])] * num_sets}
    elif isinstance(primitive, SamplerV2):
        circ.measure_all()
        return {"pubs": [(circ, param_val)] * num_sets}
    else:
        raise ValueError(f"Invalid primitive type {type(primitive)}")


def transpile_pubs(in_pubs: Iterable[Any], backend: Backend, program: str) -> list[tuple[Any, ...]]:
    """Return pubs with transformed circuits and observables."""
    t_pubs = []
    for pub in in_pubs:
        t_circ = transpile(pub[0], backend=backend)
        if program == "estimator":
            t_obs = remap_observables(pub[1], t_circ)
            t_pub = [t_circ, t_obs]
            for elem in pub[2:]:
                t_pub.append(elem)
        if program == "sampler":
            if len(pub) == 2:
                t_pub = [t_circ, pub[1]]
            else:
                t_pub = [t_circ]
        t_pubs.append(tuple(t_pub))
    return t_pubs


def remap_observables(
    observables: Iterable[str | SparsePauliOp | dict], isa_circuit: QuantumCircuit
) -> list[str | SparsePauliOp | dict]:
    """Remap observables based on input circuit."""

    def _convert_paul_or_str(_obs: str | Pauli) -> str | Pauli:
        if isinstance(_obs, str):
            return _obs + "I" * (len(layout.input_qubit_mapping) - len(_obs))
        return Pauli("X" * (len(layout.input_qubit_mapping)))

    out_obs = []
    layout = isa_circuit.layout
    for obs in observables:
        if isinstance(obs, (str, Pauli)):
            out_obs.append(_convert_paul_or_str(obs))
        elif isinstance(obs, SparsePauliOp):
            out_obs.append(obs.apply_layout(layout, num_qubits=isa_circuit.num_qubits))
        elif isinstance(obs, dict):
            mapped = {_convert_paul_or_str(key): val for key, val in obs.items()}
            out_obs.append(mapped)
        else:
            raise ValueError(f"Observable of type {type(obs)} is not supported.")

    return out_obs
