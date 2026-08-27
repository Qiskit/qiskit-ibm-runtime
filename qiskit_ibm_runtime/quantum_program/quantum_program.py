# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""QuantumProgram."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.quantum_info import PauliLindbladMap

from samplomatic.quantum_program import (  # noqa: F401,TC002
    CircuitItem,
    QuantumProgramItem,
    SamplexItem,
)
from samplomatic.quantum_program import QuantumProgram as BaseQuantumProgram
from samplomatic.quantum_program.datatree import DataTree  # noqa: TC002


class QuantumProgram(BaseQuantumProgram):
    """A quantum runtime executable.

    A quantum program consists of a list of ordered elements, each of which contains a single
    circuit and an array of associated parameter values. Executing a quantum program will
    sample the outcome of each circuit for the specified number of ``shots`` for each set of
    circuit arguments provided.

    Args:
        shots: The number of shots for each circuit execution.
        items: Items that comprise the program.
        noise_maps: Noise maps to use with samplex items.
        meas_level: The level at which to return all classical register measurement results. This
            value sets the return type of all classical registers in all quantum program items and
            determines whether the raw complex data from low-level measurement devices is
            discriminated into bits or not. The supported values are

                * "classified": Classical register data is returned as boolean arrays with the
                    intrinsic shape ``(num_shots, creg_size)``.
                * "kerneled": Classical register data is returned as a complex array with the
                    intrinsic shape ``(num_shots, creg_size)``, where each entry represents an IQ
                    data point (resulting from kerneling the measurement trace) in arbitrary units.
                * "avg_kerneled": Classical register data is returned as a complex array with the
                    intrinsic shape ``(creg_size,)``, where data is equivalent to "kerneled" except
                    additionally averaged over shots.

        passthrough_data: Arbitrary nested data passed through execution without modification.
    """

    def __init__(
        self,
        shots: int,
        items: Iterable[QuantumProgramItem] | None = None,
        noise_maps: dict[str, PauliLindbladMap] | None = None,
        meas_level: Literal["classified", "kerneled", "avg_kerneled", "both"] = "classified",
        passthrough_data: DataTree | None = None,
    ):
        super().__init__(
            shots=shots,
            items=items,
            noise_maps=noise_maps,
            meas_level=meas_level,
            passthrough_data=passthrough_data,
        )

        # Semantic role indicating how execution results may be post-processed by runtime clients.
        # Reserved system values include 'sampler-v2' and 'estimator-v2', and are subject to change
        # without notice. Third party clients should not set or depend on this value.
        self._semantic_role: str | None = None
