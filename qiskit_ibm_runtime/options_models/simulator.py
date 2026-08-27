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

"""Simulator options for executor-based primitives."""

from __future__ import annotations

from typing import Annotated, TypeAlias

from pydantic import AfterValidator, Field, InstanceOf
from qiskit.circuit import BoxOp, CircuitInstruction
from qiskit.exceptions import MissingOptionalLibraryError
from qiskit.providers import BackendV2
from qiskit.quantum_info import PauliLindbladMap
from qiskit.transpiler import CouplingMap
from qiskit.utils import optionals

from .base import BaseOptionsModel

# Dynamically define the `noise_model` field type at runtime, as `NoiseModel`
# is only a valid alternative if `qiskit_aer` is installed.
if optionals.HAS_AER:
    from qiskit_aer.noise import NoiseModel

    noise_model_type: TypeAlias = dict | Annotated[NoiseModel, InstanceOf] | None
else:
    noise_model_type: TypeAlias = dict | None  # type: ignore[no-redef, misc]


def validate_layer_noise_model(value: LayerNoiseModel | None) -> LayerNoiseModel | None:
    """Validate the ``LayerNoiseModel``."""
    if value:
        instruction, noise = value
        if not isinstance(instruction.operation, BoxOp):
            raise ValueError("Found an instruction that does not contain a box.")
        if len(instruction.qubits) != noise.num_qubits:
            raise ValueError(
                f"Found instruction with {len(instruction.qubits)}"
                f"qubits but a noise model with {noise.num_qubits}."
            )
    return value


LayerNoiseModel: TypeAlias = Annotated[
    tuple[Annotated[CircuitInstruction, InstanceOf], Annotated[PauliLindbladMap, InstanceOf]],
    AfterValidator(validate_layer_noise_model),
]


class ExperimentalSimulatorOptions(BaseOptionsModel):
    """Simulator options."""

    angle_decimals: int = 5
    """Gate angle decimal precision.

    Gate angles are rounded to the nearest multiple of ``np.pi/2`` at this decimal precision before
    simulation. This prevents floating-point drift from preventing Clifford-method simulation when
    angles are nominally Clifford.
    """

    layer_noise_model: list[LayerNoiseModel] | None = None
    """Noise model specified by a collection of instructions and the noise that affects them.

    If ``None``, it inherits the default of :attr:`~.ResilienceOptions.layer_noise_model` when
    simulating with the V2 Estimator.
    """

    seed_simulator: int | None = None
    """Random seed to control sampling."""

    warn_absent: bool = True
    """Whether to emit a warning when an entry is missing in :attr:`layer_noise_dict`."""


class SimulatorOptions(BaseOptionsModel):
    """Legacy Simulator options.

    Used to control local mode simulation.
    """

    noise_model: noise_model_type = None
    """Noise model for the simulator."""

    seed_simulator: int | None = None
    """Random seed to control sampling."""

    coupling_map: (
        list[list[Annotated[int, Field(ge=0)]]] | Annotated[CouplingMap, InstanceOf] | None
    ) = None
    """Directed coupling map to target in mapping.

    If the coupling map is symmetric, both directions need to be specified. Each entry in the list
    specifies a directed two-qubit interaction, e.g:
    ``[[0, 1], [0, 3], [1, 2], [1, 5], [2, 5], [4, 1], [5, 3]]``. ``None`` implies no connectivity
    constraints.
    """

    basis_gates: list[str] | None = None
    """List of basis gate names to unroll to.

    For example, ``['u1', 'u2', 'u3', 'cx']``. Unrolling is not done if not set.
    """

    def set_backend(self, backend: BackendV2) -> None:
        """Set backend for simulation.

        This method changes noise_model, coupling_map, basis_gates according to given backend.

        Args:
            backend: backend to be set.

        Raises:
            MissingOptionalLibraryError: if qiskit-aer is not found.
        """
        if not optionals.HAS_AER:
            raise MissingOptionalLibraryError(
                "qiskit-aer", "Aer provider", "pip install qiskit-aer"
            )

        from qiskit_aer.noise import NoiseModel as AerNoiseModel

        self.noise_model = AerNoiseModel.from_backend(backend)

        if isinstance(backend, BackendV2):
            self.coupling_map = backend.coupling_map
            self.basis_gates = backend.operation_names
