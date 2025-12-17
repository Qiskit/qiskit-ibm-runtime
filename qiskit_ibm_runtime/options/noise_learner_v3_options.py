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

import copy
from dataclasses import asdict, fields
from typing import Any
from collections.abc import Callable

from pydantic import Field, ValidationInfo, field_validator
from qiskit.transpiler import CouplingMap

from ibm_quantum_schemas.models.noise_learner_v3.version_0_1.models import (
    OptionsModel,
)

from ..runtime_options import RuntimeOptions
from .environment_options import EnvironmentOptions
from .options import BaseOptions
from .post_selection_options import PostSelectionOptions
from .simulator_options import SimulatorOptions
from .utils import (
    Unset,
    UnsetType,
    make_constraint_validator,
    merge_options_v2,
    primitive_dataclass,
    remove_dict_unset_values,
    remove_empty_dict,
    skip_unset_validation,
)


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

    post_selection: PostSelectionOptions | dict = Field(default_factory=PostSelectionOptions)
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

    def to_options_model(self) -> OptionsModel:
        """Turn these options into an ``OptionsModel`` object.

        Filters out every irrelevant field and replaces ``Unset``\\s with ``None``\\s.
        """
        options_dict = asdict(self)

        filtered_options = {}
        for key in OptionsModel.model_fields:  # pylint: disable=not-an-iterable
            filtered_options[key] = options_dict.get(key)

        remove_dict_unset_values(filtered_options)
        return OptionsModel(**filtered_options)

    def to_runtime_options(self) -> dict:
        """Turn these options into a dictionary of runtime options object.

        Filters out every irrelevant field (i.e., those that are not fields of :class:`.RuntimeOptions`)
        and replaces ``Unset``\\s with ``None``\\s.
        """
        options_dict = asdict(self)
        environment = options_dict.get("environment")

        filtered_options = {"max_execution_time": options_dict.get("max_execution_time", None)}
        for fld in fields(RuntimeOptions):
            if fld.name in environment:
                filtered_options[fld.name] = environment[fld.name]

        if "image" in options_dict:
            filtered_options["image"] = options_dict["image"]
        elif "image" in options_dict.get("experimental", {}):
            filtered_options["image"] = options_dict["experimental"]["image"]

        remove_dict_unset_values(filtered_options)
        return filtered_options

    def get_callback(self) -> Callable | None:
        """Get the callback."""
        options_dict = asdict(self)
        remove_dict_unset_values(options_dict)
        return options_dict.get("environment", {}).get("callback", None)

    # The following code is copy/pasted from OptionsV2.
    # Reason not to use OptionsV2: As stated in the docstring, it is meant for v2 primitives, and
    #     NoiseLearnerV3 is neither a primitive nor a v2.
    # Reason not to implement OptionsV3: I don't feel like committing to an API for it.

    # Options not really related to primitives.
    max_execution_time: UnsetType | int = Unset
    environment: EnvironmentOptions | dict = Field(default_factory=EnvironmentOptions)
    simulator: SimulatorOptions | dict = Field(default_factory=SimulatorOptions)

    def update(self, **kwargs: Any) -> None:
        """Update the options."""

        def _set_attr(_merged: dict) -> None:
            for key, val in _merged.items():
                if not key.startswith("_"):
                    setattr(self, key, val)

        merged = merge_options_v2(self, kwargs)
        _set_attr(merged)

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitives.
        """

        def _set_if_exists(name: str, _inputs: dict, _options: dict) -> None:
            if name in _options:
                _inputs[name] = _options[name]

        options_copy = copy.deepcopy(options)
        output_options: dict[str, Any] = {}
        sim_options = options_copy.get("simulator", {})
        coupling_map = sim_options.get("coupling_map", Unset)
        # TODO: We can just move this to json encoder
        if isinstance(coupling_map, CouplingMap):
            sim_options["coupling_map"] = list(map(list, coupling_map.get_edges()))

        for fld in [
            "default_precision",
            "default_shots",
            "seed_estimator",
            "dynamical_decoupling",
            "resilience",
            "twirling",
            "simulator",
            "execution",
        ]:
            _set_if_exists(fld, output_options, options_copy)

        # Add arbitrary experimental options
        experimental = options_copy.get("experimental", None)
        if isinstance(experimental, dict):
            new_keys = {}
            for key in list(experimental.keys()):
                if key not in output_options:
                    new_keys[key] = experimental.pop(key)
            output_options = merge_options_v2(output_options, experimental)
            if new_keys:
                output_options["experimental"] = new_keys

        # Remove image
        output_options.get("experimental", {}).pop("image", None)

        remove_dict_unset_values(output_options)
        remove_empty_dict(output_options)

        inputs = {
            "options": output_options,
        }
        if options_copy.get("resilience_level", Unset) != Unset:
            inputs["resilience_level"] = options_copy["resilience_level"]

        return inputs
