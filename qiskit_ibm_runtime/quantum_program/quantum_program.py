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
import math
from typing import TYPE_CHECKING, Any
from collections.abc import Iterable

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

    Each item has a :attr:`shape` that determines the number of circuit executions. This shape
    is computed by broadcasting the *extrinsic* shapes of all input arrays. Input arrays have
    both extrinsic axes (leftmost, defining the sweep grid) and intrinsic axes (rightmost,
    determined by the data type). For example, ``circuit_arguments`` for a circuit with ``n``
    parameters has intrinsic shape ``(n,)``, so an array of shape ``(5, 3, n)`` has extrinsic
    shape ``(5, 3)``.

    Output arrays returned by the executor follow the same convention: extrinsic axes match
    the item's :attr:`shape`, and intrinsic axes are determined by the output type (e.g.,
    ``(num_shots, creg_size)`` for classical register data).

    Args:
        circuit: The circuit to be executed.
        chunk_size: The maximum number of bound circuits in each shot loop execution, or
            ``None`` to use a server-side heuristic to optimize speed. When not executing
            in a session, the server-side heuristic is always used and this value is ignored.
    """

    def __init__(self, circuit: QuantumCircuit, chunk_size: int | None = None):
        if not isinstance(circuit, QuantumCircuit):
            raise ValueError(f"Expected {repr(circuit)} to be a QuantumCircuit.")

        self.circuit = circuit
        self.chunk_size = chunk_size

    @property
    @abc.abstractmethod
    def shape(self) -> tuple[int, ...]:
        """The extrinsic shape of this item, i.e., the broadcasted extrinsic shapes of all inputs."""

    def size(self) -> int:
        """The total number elements in this item; the product of the entries of :attr:`~.shape`."""
        return math.prod(self.shape)


class CircuitItem(QuantumProgramItem):
    """An item of a :class:`QuantumProgram` containing a circuit and its arguments.

    Args:
        circuit: The circuit to be executed.
        circuit_arguments: A real-valued array of parameter values for the circuit. The last axis
            is intrinsic with size equal to the number of circuit parameters. Leading axes are
            extrinsic and define the sweep grid. For example, shape ``(5, 3, n)`` means 5×3=15
            configurations for a circuit with ``n`` parameters.
        chunk_size: The maximum number of bound circuits in each shot loop execution, or
            ``None`` to use a server-side heuristic to optimize speed. When not executing
            in a session, the server-side heuristic is always used and this value is ignored.
    """

    def __init__(
        self,
        circuit: QuantumCircuit,
        *,
        circuit_arguments: np.ndarray | None = None,
        chunk_size: int | None = None,
    ):
        super().__init__(circuit=circuit, chunk_size=chunk_size)

        if circuit_arguments is None:
            if circuit.num_parameters:
                raise ValueError(
                    f"{repr(circuit)} is parametric, but no 'circuit_arguments' were supplied."
                )
            circuit_arguments = []

        circuit_arguments = np.array(circuit_arguments, dtype=float)

        if circuit_arguments.shape[-1] != circuit.num_parameters:
            raise ValueError(
                "Expected the last axis of 'circuit_arguments' to have size "
                f"{circuit.num_parameters} in order to match the number of parameters of the "
                f"circuit, but found shape {circuit_arguments.shape} instead."
            )

        self.circuit_arguments = circuit_arguments

    @property
    def shape(self) -> tuple[int, ...]:
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
        samplex_arguments: A map from argument names to argument values for the samplex. Each
            argument array has intrinsic axes determined by its type (e.g., ``parameter_values``
            has intrinsic shape ``(n,)`` for ``n`` parameters, while scalar inputs like
            ``noise_scale`` have intrinsic shape ``()``). The extrinsic shapes of all arguments
            are broadcasted together following NumPy conventions.
        shape: A shape that the item's extrinsic shape must be broadcastable to. Axes where
            ``shape`` exceeds the shape implicit in ``samplex_arguments`` enumerate independent
            randomizations.
        chunk_size: The maximum number of bound circuits in each shot loop execution, or
            ``None`` to use a server-side heuristic to optimize speed. When not executing
            in a session, the server-side heuristic is always used and this value is
            ignored.
    """

    def __init__(
        self,
        circuit: QuantumCircuit,
        samplex: Samplex,
        *,
        samplex_arguments: dict[str, Any] | None = None,
        shape: tuple[int, ...] | None = None,
        chunk_size: int | None = None,
    ):
        super().__init__(circuit=circuit, chunk_size=chunk_size)

        # Calling bind() here will do all Samplex validation
        inputs = samplex.inputs().make_broadcastable().bind(**(samplex_arguments or {}))

        if not inputs.fully_bound:
            raise ValueError(
                "The following required samplex arguments are missing:\n"
                f"{inputs.describe(prefix='  * ', include_bound=False)}"
            )

        try:
            self._shape = np.broadcast_shapes(shape or (), inputs.shape)
        except ValueError as exc:
            raise ValueError(
                f"The provided shape {shape} must be broadcastable with the shape implicit in "
                f"the sample_arguments, which is {inputs.shape}."
            ) from exc

        self.samplex = samplex
        self.samplex_arguments = inputs

    @property
    def shape(self) -> tuple[int, ...]:
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

    def append_circuit_item(
        self,
        circuit: QuantumCircuit,
        *,
        circuit_arguments: np.ndarray | None = None,
        chunk_size: int | None = None,
    ) -> None:
        """Append a new :class:`CircuitItem` to this program.

        Args:
            circuit: The circuit of this item.
            circuit_arguments: A real-valued array of parameter values for the circuit. The last
                axis is intrinsic with size equal to the number of circuit parameters. Leading
                axes are extrinsic and define the sweep grid.
            chunk_size: The maximum number of bound circuits in each shot loop execution, or
                ``None`` to use a server-side heuristic to optimize speed. When not executing
                in a session, the server-side heuristic is always used and this value is ignored.
        """
        self.items.append(
            CircuitItem(
                circuit,
                circuit_arguments=circuit_arguments,
                chunk_size=chunk_size,
            )
        )

    def append_samplex_item(
        self,
        circuit: QuantumCircuit,
        *,
        samplex: Samplex,
        samplex_arguments: dict[str, Any] | None = None,
        shape: tuple[int, ...] | None = None,
        chunk_size: int | None = None,
    ) -> None:
        """Append a new :class:`SamplexItem` to this program.

        Args:
            circuit: The circuit of this item.
            samplex: A samplex to draw random parameters for the circuit.
            samplex_arguments: A map from argument names to argument values for the samplex. Each
                argument array has intrinsic axes determined by its type (e.g., ``parameter_values``
                has intrinsic shape ``(n,)`` for ``n`` parameters). The extrinsic shapes of all
                arguments are broadcasted together.
            shape: A shape that the item's extrinsic shape must be broadcastable to. Axes where
                ``shape`` exceeds the shape implicit in ``samplex_arguments`` enumerate independent
                randomizations.
            chunk_size: The maximum number of bound circuits in each shot loop execution, or
                ``None`` to use a server-side heuristic to optimize speed. When not executing
                in a session, the server-side heuristic is always used and this value is ignored.
        """
        # add the noise maps first so that samplex_arguments has the ability to overwrite them
        arguments = {
            "pauli_lindblad_maps": {
                noise_name: noise_model
                for noise_name, noise_model in self.noise_maps.items()
                if f"pauli_lindblad_maps.{noise_name}"
                in [spec.name for spec in samplex.inputs().get_specs()]
            }
        }

        arguments.update(samplex_arguments or {})
        self.items.append(
            SamplexItem(
                circuit,
                samplex,
                samplex_arguments=arguments,
                shape=shape,
                chunk_size=chunk_size,
            )
        )

    def validate(self, backend: IBMBackend) -> None:
        """Validate this quantum program against the given backend."""

    def __repr__(self) -> str:
        if not self.items:
            return f"QuantumProgram(shots={self.shots})"
        return "\n".join(
            [f"QuantumProgram(shots={self.shots}, items=["]
            + [f"    {repr(item)}," for item in self.items]
            + ["])"]
        )
