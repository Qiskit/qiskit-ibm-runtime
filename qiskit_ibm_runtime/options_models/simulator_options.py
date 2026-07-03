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

from typing import TypeAlias

from pydantic import field_validator
from pydantic.dataclasses import dataclass
from qiskit.exceptions import MissingOptionalLibraryError
from qiskit.providers import BackendV2
from qiskit.transpiler import CouplingMap
from qiskit.utils import optionals

from .utils import PRIMITIVES_CONFIG

# Dynamically define the `noise_model` field type at runtime, as `NoiseModel`
# is only a valid alternative if `qiskit_aer` is installed.
if optionals.HAS_AER:
    from qiskit_aer.noise import NoiseModel as AerNoiseModel

    noise_model_type: TypeAlias = dict | AerNoiseModel | None
else:
    noise_model_type: TypeAlias = dict | None  # type: ignore[no-redef, misc]


@dataclass(config=PRIMITIVES_CONFIG)
class SimulatorOptions:
    """Simulator options.

    Used to control local mode simulation.
    """

    noise_model: noise_model_type = None
    """Noise model for the simulator."""

    seed_simulator: int | None = None
    """Random seed to control sampling."""

    coupling_map: list[list[int]] | CouplingMap | None = None
    """Directed coupling map to target in mapping.

    If the coupling map is symmetric, both directions need to be specified.
    Each entry in the list specifies a directed two-qubit interaction,
    e.g: ``[[0, 1], [0, 3], [1, 2], [1, 5], [2, 5], [4, 1], [5, 3]]``.
    ``None`` implies no connectivity constraints.
    """

    basis_gates: list[str] | None = None
    """List of basis gate names to unroll to.

    For example, ``['u1', 'u2', 'u3', 'cx']``. Unrolling is not done if not set.
    """

    @field_validator("coupling_map", mode="plain")
    @classmethod
    def _validate_coupling_map(
        cls, coupling_map: list[list[int]] | CouplingMap | None
    ) -> CouplingMap | None:
        """Validate and coerce a coupling map into a :class:`.CouplingMap`."""
        if coupling_map is None:
            return None
        elif isinstance(coupling_map, CouplingMap):
            return coupling_map
        elif isinstance(coupling_map, list):
            try:
                return CouplingMap(coupling_map)
            except Exception as exc:
                raise ValueError(f"Cannot create a valid CouplingMap from the provided list. {exc}")
        else:
            raise ValueError(
                "Expected a CouplingMap or list[list[int]] instead got"
                f"{type(coupling_map).__name__}"
            )

    @field_validator("noise_model", mode="plain")
    @classmethod
    def _validate_noise_model(cls, model: noise_model_type) -> noise_model_type:
        """Validate noise model."""
        if model is None:
            return model
        if not isinstance(model, dict):
            if not optionals.HAS_AER:
                raise ValueError(
                    "When qiskit-aer is not installed, the only allowed values for"
                    f"noise_model are dict and None, instead got {type(model).__name__}"
                )

            from qiskit_aer.noise import NoiseModel as AerNoiseModel

            if not isinstance(model, AerNoiseModel):
                raise ValueError(
                    "'noise_model' can only be a dictionary or qiskit_aer.noise.NoiseModel."
                )
        return model

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
