# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Simulator options."""

from typing import List, Union, Optional

from qiskit.exceptions import MissingOptionalLibraryError
from qiskit.providers import BackendV2
from qiskit.utils import optionals
from qiskit.transpiler import CouplingMap  # pylint: disable=unused-import

from pydantic import field_validator

from .utils import Unset, UnsetType, skip_unset_validation, primitive_dataclass


class NoiseModel:
    """Fake noise model class for pydantic."""

    pass


@primitive_dataclass
class SimulatorOptions:
    """Simulator options.

    For best practice in simulating a backend make sure to pass the
    basis gates and coupling map of that backend.

    """

    noise_model: Optional[Union[UnsetType, dict, NoiseModel]] = Unset
    r"""Noise model for the simulator. This option is only supported in
        local testing mode.

        Default: ``None``.
    """
    seed_simulator: Union[UnsetType, int] = Unset
    r"""Random seed to control sampling. 
    
        Default: ``None``.
    """
    coupling_map: Union[UnsetType, List[List[int]], CouplingMap] = Unset
    r"""Directed coupling map to target in mapping. If
        the coupling map is symmetric, both directions need to be specified.
        Each entry in the list specifies a directed two-qubit interaction,
        e.g: ``[[0, 1], [0, 3], [1, 2], [1, 5], [2, 5], [4, 1], [5, 3]]``.
    
        Default: ``None``, which implies no connectivity constraints.
    """
    basis_gates: Union[UnsetType, List[str]] = Unset
    r"""List of basis gate names to unroll to. For example,
        ``['u1', 'u2', 'u3', 'cx']``. Unrolling is not done if not set.
        
        Default: all basis gates supported by the simulator.
    """

    @field_validator("noise_model", mode="plain")
    @classmethod
    @skip_unset_validation
    def _validate_noise_model(cls, model: Union[dict, NoiseModel]) -> Union[dict, NoiseModel]:
        if not isinstance(model, dict):
            if not optionals.HAS_AER:
                raise ValueError(
                    "'noise_model' can only be a dictionary or qiskit_aer.noise.NoiseModel."
                )

            from qiskit_aer.noise import (  # pylint:disable=import-outside-toplevel
                NoiseModel as AerNoiseModel,
            )

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

        from qiskit_aer.noise import (  # pylint:disable=import-outside-toplevel
            NoiseModel as AerNoiseModel,
        )

        self.noise_model = AerNoiseModel.from_backend(backend)

        if isinstance(backend, BackendV2):
            self.coupling_map = backend.coupling_map
            self.basis_gates = backend.operation_names
