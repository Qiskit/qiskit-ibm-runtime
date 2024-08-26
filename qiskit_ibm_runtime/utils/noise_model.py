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

"""Utility functions for the qiskit aer Noise Model class."""

from warnings import catch_warnings, filterwarnings
from typing import Any, Dict, List
import numpy as np

from qiskit.circuit import Instruction
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import Reset
from qiskit.circuit.library.generalized_gates import PauliGate, UnitaryGate

from qiskit_aer.noise.errors.quantum_error import QuantumError
from qiskit_aer.noise.errors.readout_error import ReadoutError
from qiskit_aer.noise.noiseerror import NoiseError
from qiskit_aer.noise.noise_model import NoiseModel


def from_dict(noise_dict: Dict[str, Any]) -> NoiseModel:
    """
    Load NoiseModel from a dictionary.

    Args:
        noise_dict (dict): A serialized noise model.

    Returns:
        NoiseModel: the noise model.

    Raises:
        NoiseError: if dict cannot be converted to NoiseModel.
    """

    def inst_dic_list_to_circuit(dic_list: List[Any]) -> QuantumCircuit:
        num_qubits = max(max(dic["qubits"]) for dic in dic_list) + 1
        circ = QuantumCircuit(num_qubits)
        for dic in dic_list:
            if dic["name"] == "reset":
                circ.append(Reset(), qargs=dic["qubits"])
            elif dic["name"] == "kraus":
                circ.append(
                    Instruction(
                        name="kraus",
                        num_qubits=len(dic["qubits"]),
                        num_clbits=0,
                        params=dic["params"],
                    ),
                    qargs=dic["qubits"],
                )
            elif dic["name"] == "unitary":
                circ.append(UnitaryGate(data=dic["params"][0]), qargs=dic["qubits"])
            elif dic["name"] == "pauli":
                circ.append(PauliGate(dic["params"][0]), qargs=dic["qubits"])
            else:
                with catch_warnings():
                    filterwarnings(
                        "ignore",
                        category=DeprecationWarning,
                        module="qiskit_aer.noise.errors.errorutils",
                    )
                    circ.append(
                        UnitaryGate(label=dic["name"], data=_standard_gate_unitary(dic["name"])),
                        qargs=dic["qubits"],
                    )
        return circ

    # Return noise model
    noise_model = NoiseModel()

    # Get error terms
    errors = noise_dict.get("errors", [])

    for error in errors:
        error_type = error["type"]

        # Add QuantumError
        if error_type == "qerror":
            circuits = [inst_dic_list_to_circuit(dics) for dics in error["instructions"]]
            noise_ops = tuple(zip(circuits, error["probabilities"]))
            qerror = QuantumError(noise_ops)
            qerror._id = error.get("id", None) or qerror.id
            instruction_names = error["operations"]
            all_gate_qubits = error.get("gate_qubits", None)
            if all_gate_qubits is not None:
                for gate_qubits in all_gate_qubits:
                    # Add local quantum error
                    noise_model.add_quantum_error(
                        qerror, instruction_names, gate_qubits, warnings=False
                    )
            else:
                # Add all-qubit quantum error
                noise_model.add_all_qubit_quantum_error(qerror, instruction_names, warnings=False)

        # Add ReadoutError
        elif error_type == "roerror":
            probabilities = error["probabilities"]
            all_gate_qubits = error.get("gate_qubits", None)
            roerror = ReadoutError(probabilities)
            # Add local readout error
            if all_gate_qubits is not None:
                for gate_qubits in all_gate_qubits:
                    noise_model.add_readout_error(roerror, gate_qubits, warnings=False)
            # Add all-qubit readout error
            else:
                noise_model.add_all_qubit_readout_error(roerror, warnings=False)
        # Invalid error type
        else:
            raise NoiseError("Invalid error type: {}".format(error_type))
    return noise_model


def _standard_gate_unitary(name: str) -> np.ndarray:
    # To be removed with from_dict
    unitary_matrices = {
        ("id", "I"): np.eye(2, dtype=complex),
        ("x", "X"): np.array([[0, 1], [1, 0]], dtype=complex),
        ("y", "Y"): np.array([[0, -1j], [1j, 0]], dtype=complex),
        ("z", "Z"): np.array([[1, 0], [0, -1]], dtype=complex),
        ("h", "H"): np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
        ("s", "S"): np.array([[1, 0], [0, 1j]], dtype=complex),
        ("sdg", "Sdg"): np.array([[1, 0], [0, -1j]], dtype=complex),
        ("t", "T"): np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
        ("tdg", "Tdg"): np.array([[1, 0], [0, np.exp(-1j * np.pi / 4)]], dtype=complex),
        ("cx", "CX", "cx_01"): np.array(
            [[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]], dtype=complex
        ),
        ("cx_10",): np.array(
            [[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]], dtype=complex
        ),
        ("cz", "CZ"): np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, -1]], dtype=complex
        ),
        ("swap", "SWAP"): np.array(
            [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex
        ),
        ("ccx", "CCX", "ccx_012", "ccx_102"): np.array(
            [
                [1, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 1, 0, 0, 0, 0],
            ],
            dtype=complex,
        ),
        ("ccx_021", "ccx_201"): np.array(
            [
                [1, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 1, 0, 0],
            ],
            dtype=complex,
        ),
        ("ccx_120", "ccx_210"): np.array(
            [
                [1, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 1, 0],
            ],
            dtype=complex,
        ),
    }

    return next((value for key, value in unitary_matrices.items() if name in key), None)
