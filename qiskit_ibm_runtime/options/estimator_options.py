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

"""Primitive options."""

from typing import Optional, Union, ClassVar, Literal, get_args, Any
import copy

from qiskit.transpiler import CouplingMap
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic import Field, ConfigDict, model_validator, field_validator

from .utils import Dict, Unset, UnsetType, _remove_dict_unset_values
from .execution_options import ExecutionOptionsV2
from .transpilation_options import TranspilationOptions
from .resilience_options import ResilienceOptionsV2
from .twirling_options import TwirlingOptions
from .options import OptionsV2

DDSequenceType = Literal["XX", "XpXm", "XY4"]


class EstimatorOptions(OptionsV2):
    pass


@pydantic_dataclass(config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=True, extra="forbid"))
class EstimatorOptionsV2(EstimatorOptions):
    """Options for v2 Estimator.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation times. This is based on the
            ``optimization_level`` parameter in qiskit-terra but may include
            backend-specific optimization. Default: 1.

            * 0: no optimization
            * 1: light optimization
            * 2: heavy optimization
            * 3: even heavier optimization

        resilience_level: How much resilience to build against errors.
            Higher levels generate more accurate results,
            at the expense of longer processing times. Default: 1.

            * 0: No mitigation.
            * 1: Minimal mitigation costs. Mitigate error associated with readout errors.
            * 2: Medium mitigation costs. Typically reduces bias in estimators but
              is not guaranteed to be zero bias. Only applies to estimator.
            * 3: Heavy mitigation with layer sampling. Theoretically expected to deliver zero
              bias estimators. Only applies to estimator.

            Refer to the
            `Qiskit Runtime documentation
            <https://qiskit.org/documentation/partners/qiskit_ibm_runtime>`_.
            for more information about the error mitigation methods used at each level.

        dynamical_decoupling: Optional, specify a dynamical decoupling sequence to use.
            Allowed values are ``"XX"``, ``"XpXm"``, ``"XY4"``.
            Default: None

        transpilation: Transpilation options. See :class:`TranspilationOptions` for all
            available options.

        resilience: Advanced resilience options to fine tune the resilience strategy.
            See :class:`ResilienceOptions` for all available options.

        execution: Execution time options. See :class:`ExecutionOptions` for all available options.

        environment: Options related to the execution environment. See
            :class:`EnvironmentOptions` for all available options.

        simulator: Simulator options. See
            :class:`SimulatorOptions` for all available options.

    """
    _version: int = 2
    _is_simulator: bool = False

    _MAX_OPTIMIZATION_LEVEL = 3
    _MAX_RESILIENCE_LEVEL = 3

    # Sadly we cannot use pydantic's built in validation because it won't work on Unset.
    optimization_level: Union[UnsetType, int] = Unset
    resilience_level: Union[UnsetType, int] = Unset
    dynamical_decoupling: Union[UnsetType, DDSequenceType] = Unset
    transpilation: Union[TranspilationOptions, Dict] = Field(default_factory=TranspilationOptions)
    resilience: Union[ResilienceOptionsV2, Dict] = Field(default_factory=ResilienceOptionsV2)
    execution: Union[ExecutionOptionsV2, Dict] = Field(default_factory=ExecutionOptionsV2)
    twirling: Union[TwirlingOptions, Dict] = Field(default_factory=TwirlingOptions)
    experimental: Union[UnsetType, dict] = Unset

    @field_validator("optimization_level")
    @classmethod
    def _validate_optimization_level(cls, optimization_level: Union[UnsetType, int]):
        """Validate optimization_leve."""
        if not isinstance(optimization_level, UnsetType) and not (0 <= optimization_level <= 3):
            raise ValueError(f"Invalid optimization_level. Valid range is 0-{EstimatorOptionsV2._MAX_OPTIMIZATION_LEVEL}")
        return optimization_level

    @field_validator("resilience_level")
    @classmethod
    def _validate_resilience_level(cls, resilience_level: Union[UnsetType, int]):
        """Validate resilience_level."""
        if not isinstance(resilience_level, UnsetType) and not (0 <= resilience_level <= 3):
            raise ValueError(f"Invalid optimization_level. Valid range is 0-{EstimatorOptionsV2._MAX_RESILIENCE_LEVEL}")
        return resilience_level

    @model_validator(mode='after')
    def _validate_options(self):
        """Validate the model."""
        # TODO: Server should have different optimization/resilience levels for simulator
        # TODO: Allow bypasing validation

        if self.resilience_level == 3 and self._is_simulator and not self.simulator.coupling_map:
            raise ValueError(
                "When the backend is a simulator and resilience_level == 3,"
                "a coupling map is required."
            )

        return self

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitives.
        """

        sim_options = options.get("simulator", {})
        inputs = {}
        inputs["transpilation"] = copy.copy(options.get("transpilation", {}))
        inputs["skip_transpilation"] = inputs["transpilation"].pop("skip_transpilation")
        coupling_map = sim_options.get("coupling_map", None)
        # TODO: We can just move this to json encoder
        if isinstance(coupling_map, CouplingMap):
            coupling_map = list(map(list, coupling_map.get_edges()))
        inputs["transpilation"].update(
            {
                "optimization_level": options.get("optimization_level"),
                "coupling_map": coupling_map,
                "basis_gates": sim_options.get("basis_gates", None),
            }
        )

        inputs["resilience_level"] = options.get("resilience_level")
        inputs["resilience"] = options.get("resilience", {})

        # TODO: Turn off ZNE/PEC fields
            # Turn off all ZNE fields
        #     self.zne_extrapolator = Unset
        #     self.zne_noise_factors = Unset
        #     self.zne_stderr_threshold = Unset

        # # Validate PEC options
        # if isinstance(self.pec_mitigation, UnsetType):
        #     self.pec_max_overhead = Unset

        inputs["twirling"] = options.get("twirling", {})

        inputs["execution"] = options.get("execution")
        inputs["execution"].update(
            {
                "noise_model": sim_options.get("noise_model", None),
                "seed_simulator": sim_options.get("seed_simulator", None),
            }
        )

        inputs["_experimental"] = True
        inputs["version"] = EstimatorOptionsV2._version
        _remove_dict_unset_values(inputs)

        return inputs


# @dataclass(frozen=True)
# class _ResilienceLevel0Options:
#     resilience_level: int = 0
#     resilience: ResilienceOptions = field(
#         default_factory=lambda: ResilienceOptions(
#             measure_noise_mitigation=False, zne_mitigation=False, pec_mitigation=False
#         )
#     )
#     twirling: TwirlingOptions = field(
#         default_factory=lambda: TwirlingOptions(gates=False, measure=False)
#     )


# @dataclass(frozen=True)
# class _ResilienceLevel1Options:
#     resilience_level: int = 1
#     resilience: ResilienceOptions = field(
#         default_factory=lambda: ResilienceOptions(
#             measure_noise_mitigation=True, zne_mitigation=False, pec_mitigation=False
#         )
#     )
#     twirling: TwirlingOptions = field(
#         default_factory=lambda: TwirlingOptions(gates=False, measure=True, strategy="active-accum")
#     )


# @dataclass(frozen=True)
# class _ResilienceLevel2Options:
#     resilience_level: int = 2
#     resilience: ResilienceOptions = field(
#         default_factory=lambda: ResilienceOptions(
#             measure_noise_mitigation=True, pec_mitigation=False, **asdict(_ZneOptions())
#         )
#     )
#     twirling: TwirlingOptions = field(
#         default_factory=lambda: TwirlingOptions(gates=True, measure=True, strategy="active-accum")
#     )


# @dataclass(frozen=True)
# class _ResilienceLevel3Options:
#     resilience_level: int = 3
#     resilience: ResilienceOptions = field(
#         default_factory=lambda: ResilienceOptions(
#             measure_noise_mitigation=True, zne_mitigation=False, **asdict(_PecOptions())
#         )
#     )
#     twirling: TwirlingOptions = field(
#         default_factory=lambda: TwirlingOptions(gates=True, measure=True, strategy="active")
#     )


# _DEFAULT_RESILIENCE_LEVEL_OPTIONS = {
#     0: _ResilienceLevel0Options(),
#     1: _ResilienceLevel1Options(),
#     2: _ResilienceLevel2Options(),
#     3: _ResilienceLevel3Options(),
# }
