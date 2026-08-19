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

"""Layer noise model class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from qiskit.circuit import BoxOp
from samplomatic import InjectNoise, Tag
from samplomatic.utils import get_annotation

if TYPE_CHECKING:
    from qiskit.circuit import CircuitInstruction
    from qiskit.quantum_info import PauliLindbladMap


class LayerNoiseModel:
    r"""A noise model for a set of circuit layers, represented in Pauli Lindblad format.

    Each layer is paired with a :class:`~qiskit.quantum_info.PauliLindbladMap` that
    describes the Pauli Lindblad noise acting on that layer.

    Args:
        layers: The circuit layers to which noise is associated.
        pauli_lindblad_maps: The :class:`~qiskit.quantum_info.PauliLindbladMap` for
            each layer in ``layers``, in the same order.

    Raises:
        ValueError: If the length of ``pauli_lindblad_maps`` does not match the
            length of ``layers``.
    """

    def __init__(
        self, layers: list[CircuitInstruction], pauli_lindblad_maps: list[PauliLindbladMap]
    ):
        if len(pauli_lindblad_maps) != len(layers):
            raise ValueError(
                f"Number of ``pauli_lindblad_maps`` ({len(pauli_lindblad_maps)}) does not match "
                f"``layers`` ({len(layers)})"
            )
        self.pauli_lindblad_maps = pauli_lindblad_maps
        self.layers = layers

    def to_dict(
        self,
        mode: Literal["injection", "simulation"] = "injection",
        require_refs: bool = False,
    ) -> dict[str, PauliLindbladMap]:
        """Convert to a dictionary from references to :class:`PauliLindbladMap` objects.

        Args:
            mode: If ``"simulation"``, it groups by :class:`~.Tag` annotations. Otherwise, by
                :class:`~.InjectNoise` annotations.
            require_refs: Whether to raise if some of the instructions do not own an
                annotation. If ``False``, all the instructions that do not contain an
                annotation are simply skipped when constructing the returned dictionary.
        """
        noise_source = {}
        num_instr = 0
        annotation_type = Tag if mode == "simulation" else InjectNoise
        for instr, pauli_map in zip(self.layers, self.pauli_lindblad_maps):
            if not isinstance(instr.operation, BoxOp):
                raise ValueError("Found an instruction that does not contain a box.")
            if annotation := get_annotation(instr.operation, annotation_type):
                num_instr += 1
                noise_source[annotation.ref] = pauli_map
            elif require_refs:
                raise ValueError(
                    "Found an instruction without an inject noise annotation. "
                    "Consider setting 'require_refs' to ``False``."
                )

        if num_instr != len(noise_source):
            raise ValueError("Found multiple instructions with the same ``ref``.")

        return noise_source
