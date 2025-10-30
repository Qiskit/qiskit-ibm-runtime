# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""QuantumProgram"""

from __future__ import annotations

import abc
from typing import Iterable, TYPE_CHECKING, Any

import numpy as np
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap
from samplomatic.samplex import Samplex


if TYPE_CHECKING:
    from ..ibm_backend import IBMBackend


def _desc_arr(arr: Any) -> str:
    if hasattr(arr, "shape") and hasattr(arr, "dtype"):
        return f"<{arr.shape}, {arr.dtype}>"
    return f"<{type(arr).__name__}>"


class QuantumProgramItem(abc.ABC):
    """An item of a :class:`QuantumProgram`.

    Args:
        circuit: The circuit to be executed.
        chunk_size: The maximum number of bound circuits in each shot loop execution.
    """

    def __init__(self, circuit: QuantumCircuit, chunk_size: int | None = None):
        if not isinstance(circuit, QuantumCircuit):
            raise ValueError(f"Expected {repr(circuit)} to be a QuantumCircuit.")

        self.circuit = circuit
        self.chunk_size = chunk_size

    @property
    @abc.abstractmethod
    def shape(self) -> tuple[int]:
        """The shape of this item when broadcasted over all arguments."""


class CircuitItem(QuantumProgramItem):
    """An item of a :class:`QuantumProgram` containing a circuit and its arguments.

    Args:
        circuit: The circuit to be executed.
        circuit_arguments: Arguments for the parameters of the circuit.
        chunk_size: The maximum number of bound circuits in each shot loop execution.
    """

    def __init__(
        self,
        circuit: QuantumCircuit,
        *,
        circuit_arguments: np.ndarray | None = None,
        chunk_size: int | None = None,
    ):
        if circuit_arguments is None and circuit.num_parameters:
            raise ValueError(
                f"{repr(circuit)} is parametric, but no 'circuit_arguments' were supplied."
            )

        if circuit_arguments is None:
            circuit_arguments = np.empty((circuit.num_parameters,), dtype=float)
        else:
            circuit_arguments = np.array(circuit_arguments, dtype=float)

        if circuit_arguments.shape[-1] != circuit.num_parameters:
            raise ValueError(
                "Expected the last axis of 'circuit_arguments' to have size "
                f"{circuit.num_parameters} in order to match the number of parameters of the "
                f"circuit, but found shape {circuit_arguments.shape} instead."
            )

        super().__init__(circuit=circuit, chunk_size=chunk_size)
        self.circuit_arguments = circuit_arguments

    @property
    def shape(self) -> tuple[int]:
        return self.circuit_arguments.shape[:-1]

    def __repr__(self) -> str:
        circuit = f"<QuantumCircuit @ {hex(id(self.circuit))}>"

        if not self.circuit_arguments.size:
            circuit_args = ""
        else:
            circuit_args = f", circuit_arguments={_desc_arr(self.circuit_arguments)}"

        chunk_size = "" if self.chunk_size is None else f", chunk_size={self.chunk_size}"

        return f"QuantumProgramSimpleItem({circuit}{circuit_args}{chunk_size})"


class SamplexItem(QuantumProgramItem):
    """An item of a :class:`QuantumProgram` containing a circuit and samplex to feed it arguments.

    Args:
        circuit: The circuit to be executed.
        samplex: A samplex to draw random parameters for the circuit.
        samplex_arguments: A map from argument names to argument values for the samplex.
        shape: A shape tuple to extend the implicit shape defined by ``samplex_arguments``.
            Non-trivial axes introduced by this extension enumerate randomizations.
        chunk_size: The maximum number of bound circuits in each shot loop execution.
    """

    def __init__(
        self,
        circuit: QuantumCircuit,
        samplex: Samplex,
        *,
        samplex_arguments: dict[str, np.ndarray | PauliLindbladMap] | None = None,
        shape: tuple[int, ...] | None = None,
        chunk_size: int | None = None,
    ):
        if not isinstance(circuit, QuantumCircuit):
            raise ValueError(f"Expected {repr(circuit)} to be a QuantumCircuit.")

        # Calling bind() here will do all Samplex validation
        inputs = samplex.inputs().make_broadcastable().bind(**samplex_arguments)

        if not inputs.fully_bound:
            raise ValueError(
                "The following required samplex arguments are missing:\n"
                f"{inputs.describe(prefix='  * ', include_bound=False)}"
            )

        try:
            shape = np.broadcast_shapes(shape or (), inputs.shape)
        except ValueError as exc:
            raise ValueError(
                f"The provided shape {shape} must be broadcastable with the shape implicit in "
                f"the sample_arguments, which is {inputs.shape}."
            ) from exc

        super().__init__(circuit=circuit, chunk_size=chunk_size)
        self._shape = np.broadcast_shapes(shape, inputs.shape)
        self.samplex = samplex
        self.samplex_arguments = inputs

    @property
    def shape(self) -> tuple[int]:
        return self._shape

    def __repr__(self) -> str:
        circuit = f"<QuantumCircuit @ {hex(id(self.circuit))}>"

        samplex = f", <Samplex @ {hex(id(self.samplex))}>" if self.samplex is not None else ""

        if not self.samplex_arguments:
            samplex_args = ""
        else:
            content = ", ".join(
                f"'{name}'={_desc_arr(val)}" for name, val in self.samplex_arguments.items()
            )
            samplex_args = f", samplex_arguments={{{content}}}"

        shape = f", shape={self.shape}"
        chunk_size = "" if self.chunk_size is None else f", chunk_size={self.chunk_size}"

        return f"QuantumProgramSamplexItem({circuit}{samplex}{samplex_args}{shape}{chunk_size})"


class QuantumProgram:
    """A quantum runtime executable.

    A quantum program consists of a list of ordered elements, each of which contains a single
    circuit and an array of associated parameter values. Executing a quantum program will
    sample the outcome of each circuit for the specified number of ``shots`` for each set of
    circuit arguments provided.

    Args:
        shots: The number of shots for each circuit execution.
        items: Items that comprise the program.
        noise_maps: Noise maps to use with samplex items.
    """

    def __init__(
        self,
        shots: int,
        items: Iterable[QuantumProgramItem] | None = None,
        noise_maps: dict[str, PauliLindbladMap] | None = None,
    ):
        self.shots = shots
        self.items: list[QuantumProgramItem] = list(items or [])
        self.noise_maps = noise_maps or {}

    def append(
        self,
        circuit: QuantumCircuit,
        *,
        samplex: Samplex | None = None,
        circuit_arguments: np.ndarray | None = None,
        samplex_arguments: dict[str, np.ndarray] | None = None,
        shape: tuple[int, ...] | None = None,
        chunk_size: int | None = None,
    ) -> None:
        """Append a new :class:`QuantumProgramItem` to this program.

        Args:
            circuit: The circuit of this item.
            samplex: An (optional) samplex to draw random parameters for the circuit.
            circuit_arguments: Arguments for the parameters of the circuit. A real array where the
                last dimension matches the number of parameters in the circuit. Circuit execution
                will be broadcasted over the leading axes.
            samplex_arguments: A map from argument names to argument values for the samplex. If this
                value is provided, a samplex must be present, and ``circuit_arguments`` must not be
                supplied.
            shape: A shape tuple to extend the implicit shape defined by ``samplex_arguments``.
                Non-trivial axes introduced by this extension enumerate randomizations. If this
                value is provided, a samplex must be present, and ``circuit_arguments`` must not be
                supplied.
            chunk_size: The maximum number of bound circuits in each shot loop execution.
        """
        if samplex is None:
            if samplex_arguments is not None:
                raise ValueError("'samplex_arguments' cannot be supplied when no samplex is given.")
            if shape is not None:
                raise ValueError("'shape' cannot be supplied when no samplex is given.")
            self.items.append(
                CircuitItem(
                    circuit,
                    circuit_arguments=circuit_arguments,
                    chunk_size=chunk_size,
                )
            )
        else:
            if circuit_arguments is not None:
                raise ValueError("'circuit_arguments' cannot be supplied when a samplex is given.")
            # add the noise maps first so that samplex_arguments has the ability to overwrite them
            arguments = {"pauli_lindblad_maps": self.noise_maps}
            arguments.update(samplex_arguments)
            self.items.append(
                SamplexItem(
                    circuit,
                    samplex,
                    samplex_arguments=arguments,
                    shape=shape,
                    chunk_size=chunk_size,
                )
            )

    def choose_chunk_sizes(self) -> None:
        """Automatically choose chunk sizes based on a heuristic."""
        for item in self.items:
            # TODO: use heuristic based on circuit, shape characteristics
            item.chunk_size = 100

    def validate(self, backend: "IBMBackend") -> None:
        """Validate this quantum program against the given backend."""

    def __repr__(self) -> str:
        if not self.items:
            return f"QuantumProgram(shots={self.shots})"
        return "\n".join(
            [f"QuantumProgram(shots={self.shots}, items=["]
            + [f"    {repr(item)}," for item in self.items]
            + ["])"]
        )
