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

"""NoiseLearnerV3Options options."""

from __future__ import annotations

from dataclasses import asdict

from pydantic import Field, ValidationInfo, field_validator, BaseModel

from ibm_quantum_schemas.models.noise_learner_v3.version_0_1.models import (
    OptionsModel as OptionsModel_0_1,
)

from .environment_options import EnvironmentOptions
from .options import BaseOptions
from .post_selection_options import PostSelectionOptions
from .simulator_options import SimulatorOptions
from .utils import (
    Dict,
    Unset,
    UnsetType,
    make_constraint_validator,
    primitive_dataclass,
    skip_unset_validation,
)


AVAILABLE_OPTIONS_MODELS = {"v0.1": OptionsModel_0_1}


@primitive_dataclass
class NoiseLearnerV3Options(BaseOptions):
    """
    Options for :class:`.NoiseLearnerV3`.
    """

    shots_per_randomization: int = 128
    r"""The total number of shots to use per randomized learning circuit."""

    num_randomizations: int = 32
    r"""The number of random circuits to use per learning circuit configuration.

    For TREX experiments, a configuration is a measurement basis.

    For Pauli Lindblad experiments, a configuration is a measurement basis and depth setting.
    For example, if your experiment has six depths, then setting this value to ``32`` will result
    in a total of ``32 * 9 * 6`` circuits that need to be executed (where ``9`` is the number
    of circuits that need to be implemented to measure all the required observables, see the
    note in the docstring for :class:`~.NoiseLearnerOptions` for mode details), at
    :attr:`~shots_per_randomization` each.
    """

    layer_pair_depths: list[int] = (0, 1, 2, 4, 16, 32)  # type: ignore[assignment]
    r"""The circuit depths (measured in number of pairs) to use in Pauli Lindblad experiments.
    
    Pairs are used as the unit because we exploit the order-2 nature of our entangling gates in
    the noise learning implementation. For example, a value of ``3`` corresponds to 6 repetitions
    of the layer of interest.
    
    .. note::
        This field is ignored by TREX experiments.
    """

    post_selection: PostSelectionOptions | Dict = Field(default_factory=PostSelectionOptions)
    r"""Options for post selecting the results of noise learning circuits.
    """

    experimental: UnsetType | dict = Unset
    r"""Experimental options. 
    
    These options are subject to change without notification, and stability is not guaranteed.
    """

    _ge0 = make_constraint_validator(
        "num_randomizations", "shots_per_randomization", ge=1  # type: ignore[arg-type]
    )

    @field_validator("layer_pair_depths", mode="after")
    @classmethod
    @skip_unset_validation
    def _nonnegative_list(cls, value: list[int], info: ValidationInfo) -> list[int]:
        if any(i < 0 for i in value):
            raise ValueError(f"`{cls.__name__}.{info.field_name}` option value must all be >= 0.")
        return value

    def to_options_model(self, schema_version: str) -> BaseModel:
        """Turn these options into an ``OptionsModel`` object.
        Filters out every irrelevant field (i.e., those that are not fields of :class:`.OptionsModel`).
        """
        try:
            options_model = AVAILABLE_OPTIONS_MODELS[schema_version]
        except KeyError:
            raise ValueError(f"No option model found for schema version {schema_version}.")

        options_dict = asdict(self)

        filtered_options = {}
        for key in options_model.model_fields:  # pylint: disable=not-an-iterable
            filtered_options[key] = options_dict.get(key)

        return options_model(**filtered_options)

    def to_runtime_options(self) -> dict:
        """Turn these options into a dictionary of runtime options object.
        Filters out every irrelevant field (i.e., those that are not fields of :class:`.RuntimeOptions`)
        and replaces ``Unset``\\s with ``None``\\s.
        """
        return self._get_runtime_options(asdict(self))

    # The following code is copy/pasted from OptionsV2.
    # Reason not to use OptionsV2: As stated in the docstring, it is meant for v2 primitives, and
    #     NoiseLearnerV3 is neither a primitive nor a v2.
    # Reason not to implement OptionsV3: I don't feel like committing to an API for it.

    # Options not really related to primitives.
    max_execution_time: UnsetType | int = Unset
    environment: EnvironmentOptions | Dict = Field(default_factory=EnvironmentOptions)
    simulator: SimulatorOptions | Dict = Field(default_factory=SimulatorOptions)

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitives.
        """
        raise NotImplementedError("Not implemented by `NoiseLearnerV3Options`.")
