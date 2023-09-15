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

from typing import Optional, Union, ClassVar, Literal, get_args
from dataclasses import dataclass, fields, field, asdict
import copy
import warnings

from qiskit.transpiler import CouplingMap

from .utils import _flexible, Dict, _remove_dict_none_values
from .environment_options import EnvironmentOptions
from .execution_options import ExecutionOptions
from .simulator_options import SimulatorOptions
from .transpilation_options import TranspilationOptions
from .resilience_options import ResilienceOptions, _ZneOptions, _PecOptions
from .twirling_options import TwirlingOptions
from ..runtime_options import RuntimeOptions

DDSequenceType = Literal[None, "XX", "XpXm", "XY4"]


@_flexible
@dataclass
class Options:
    """Options for the primitives.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation times. This is based on the
            ``optimization_level`` parameter in qiskit-terra but may include
            backend-specific optimization. Default: 3.

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

        max_execution_time: Maximum execution time in seconds. If
            a job exceeds this time limit, it is forcibly cancelled. If ``None``, the
            maximum execution time of the primitive is used.
            This value must be in between 300 seconds and the
            `system imposed maximum
            <https://qiskit.org/documentation/partners/qiskit_ibm_runtime/faqs/max_execution_time.html>`_.

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

    # Defaults for optimization_level and for resilience_level will be assigned
    # in Sampler/Estimator
    _DEFAULT_OPTIMIZATION_LEVEL = 3
    _DEFAULT_NOISELESS_OPTIMIZATION_LEVEL = 1
    _DEFAULT_RESILIENCE_LEVEL = 1
    _DEFAULT_NOISELESS_RESILIENCE_LEVEL = 0
    _MAX_OPTIMIZATION_LEVEL = 3
    _MAX_RESILIENCE_LEVEL_ESTIMATOR = 3
    _MAX_RESILIENCE_LEVEL_SAMPLER = 1
    _MIN_EXECUTION_TIME = 300
    _MAX_EXECUTION_TIME = 8 * 60 * 60  # 8 hours for real device

    optimization_level: Optional[int] = None
    resilience_level: Optional[int] = None
    max_execution_time: Optional[int] = None
    dynamical_decoupling: Optional[DDSequenceType] = None
    transpilation: Union[TranspilationOptions, Dict] = field(default_factory=TranspilationOptions)
    resilience: Union[ResilienceOptions, Dict] = field(default_factory=ResilienceOptions)
    execution: Union[ExecutionOptions, Dict] = field(default_factory=ExecutionOptions)
    environment: Union[EnvironmentOptions, Dict] = field(default_factory=EnvironmentOptions)
    simulator: Union[SimulatorOptions, Dict] = field(default_factory=SimulatorOptions)
    twirling: Union[TwirlingOptions, Dict] = field(default_factory=TwirlingOptions)

    _obj_fields: ClassVar[dict] = {
        "transpilation": TranspilationOptions,
        "execution": ExecutionOptions,
        "environment": EnvironmentOptions,
        "simulator": SimulatorOptions,
        "resilience": ResilienceOptions,
        "twirling": TwirlingOptions,
    }

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
        inputs["twirling"] = options.get("twirling", {})

        inputs["execution"] = options.get("execution")
        inputs["execution"].update(
            {
                "noise_model": sim_options.get("noise_model", None),
                "seed_simulator": sim_options.get("seed_simulator", None),
            }
        )

        known_keys = list(Options.__dataclass_fields__.keys())
        known_keys.append("image")
        # Add additional unknown keys.
        for key in options.keys():
            if key not in known_keys:
                warnings.warn(f"Key '{key}' is an unrecognized option. It may be ignored.")
                inputs[key] = options[key]

        inputs["_experimental"] = True
        return inputs

    @staticmethod
    def validate_options(options: dict) -> None:
        """Validate that program inputs (options) are valid
        Raises:
            ValueError: if optimization_level is outside the allowed range.
            ValueError: if max_execution_time is outside the allowed range.
        """
        if not options.get("optimization_level") in list(
            range(Options._MAX_OPTIMIZATION_LEVEL + 1)
        ):
            raise ValueError(
                f"optimization_level can only take the values "
                f"{list(range(Options._MAX_OPTIMIZATION_LEVEL + 1))}"
            )

        dd = options.get("dynamical_decoupling")
        if dd not in get_args(DDSequenceType):
            raise ValueError(
                f"Unsupported value '{dd}' for dynamical_decoupling. Allowed values are {get_args(DDSequenceType)}"
            )

        TwirlingOptions.validate_twirling_options(options.get("twirling"))
        ResilienceOptions.validate_resilience_options(options.get("resilience"))
        TranspilationOptions.validate_transpilation_options(options.get("transpilation"))
        execution_time = options.get("max_execution_time")
        if not execution_time is None:
            if (
                execution_time < Options._MIN_EXECUTION_TIME
                or execution_time > Options._MAX_EXECUTION_TIME
            ):
                raise ValueError(
                    f"max_execution_time must be between "
                    f"{Options._MIN_EXECUTION_TIME} and {Options._MAX_EXECUTION_TIME} seconds."
                )

        EnvironmentOptions.validate_environment_options(options.get("environment"))
        ExecutionOptions.validate_execution_options(options.get("execution"))
        SimulatorOptions.validate_simulator_options(options.get("simulator"))

    @staticmethod
    def _get_runtime_options(options: dict) -> dict:
        """Extract runtime options.

        Returns:
            Runtime options.
        """
        environment = options.get("environment") or {}
        out = {"max_execution_time": options.get("max_execution_time", None)}

        for fld in fields(RuntimeOptions):
            if fld.name in environment:
                out[fld.name] = environment[fld.name]

        if "image" in options:
            out["image"] = options["image"]

        return out

    @staticmethod
    def _merge_options(old_options: dict, new_options: Optional[dict] = None) -> dict:
        """Merge current options with the new ones.

        Args:
            new_options: New options to merge.

        Returns:
            Merged dictionary.
        """

        def _update_options(old: dict, new: dict, matched: Optional[dict] = None) -> None:
            if not new and not matched:
                return
            matched = matched or {}

            for key, val in old.items():
                if isinstance(val, dict):
                    matched = new.pop(key, {})
                    _update_options(val, new, matched)
                elif key in new.keys():
                    new_val = new.pop(key)
                    if new_val is not None:
                        old[key] = new_val
                elif key in matched.keys():
                    new_val = matched.pop(key)
                    if new_val is not None:
                        old[key] = new_val

            # Add new keys.
            for key, val in matched.items():
                old[key] = val

        combined = copy.deepcopy(old_options)
        if not new_options:
            return combined
        new_options_copy = copy.deepcopy(new_options)

        # First update values of the same key.
        _update_options(combined, new_options_copy)

        # Add new keys.
        combined.update(new_options_copy)

        return combined

    @classmethod
    def _merge_options_with_defaults(
        cls,
        primitive_options: dict,
        overwrite_options: Optional[dict] = None,
        is_simulator: bool = False,
    ):
        def _get_merged_value(name, first: dict = None, second: dict = None):
            first = first or overwrite_options
            second = second or primitive_options
            return first.get(name) or second.get(name)

        # 1. Determine optimization and resilience levels
        optimization_level = _get_merged_value("optimization_level")
        resilience_level = _get_merged_value("resilience_level")
        noise_model = _get_merged_value(
            "noise_model",
            first=overwrite_options.get("simulator", {}),
            second=primitive_options.get("simulator", {}),
        )
        if optimization_level is None:
            optimization_level = (
                cls._DEFAULT_NOISELESS_OPTIMIZATION_LEVEL
                if (is_simulator and noise_model is None)
                else cls._DEFAULT_OPTIMIZATION_LEVEL
            )
        if resilience_level is None:
            resilience_level = (
                cls._DEFAULT_NOISELESS_RESILIENCE_LEVEL
                if (is_simulator and noise_model is None)
                else cls._DEFAULT_RESILIENCE_LEVEL
            )

        # 2. Determine the default resilience options
        if resilience_level not in _DEFAULT_RESILIENCE_LEVEL_OPTIONS.keys():
            raise ValueError(f"resilience_level {resilience_level} is not a valid value.")
        default_options = asdict(_DEFAULT_RESILIENCE_LEVEL_OPTIONS[resilience_level])
        default_options["optimization_level"] = optimization_level

        # 3. Merge in primitive options.
        final_options = Options._merge_options(default_options, primitive_options)

        # 4. Merge in overwrites.
        final_options = Options._merge_options(final_options, overwrite_options)

        # 5. Remove Nones
        _remove_dict_none_values(final_options)

        return final_options


@dataclass(frozen=True)
class _ResilienceLevel0Options:
    resilience_level: int = 0
    resilience: ResilienceOptions = field(
        default=ResilienceOptions(
            measure_noise_mitigation=False, zne_mitigation=False, pec_mitigation=False
        )
    )
    twirling: TwirlingOptions = field(default=TwirlingOptions(gates=False, measure=False))


@dataclass(frozen=True)
class _ResilienceLevel1Options:
    resilience_level: int = 1
    resilience: ResilienceOptions = field(
        default=ResilienceOptions(
            measure_noise_mitigation=True, zne_mitigation=False, pec_mitigation=False
        )
    )
    twirling: TwirlingOptions = field(
        default=TwirlingOptions(gates=True, measure=True, strategy="active-accum")
    )


@dataclass(frozen=True)
class _ResilienceLevel2Options:
    resilience_level: int = 2
    resilience: ResilienceOptions = field(
        default=ResilienceOptions(
            measure_noise_mitigation=True, pec_mitigation=False, **asdict(_ZneOptions())
        )
    )
    twirling: TwirlingOptions = field(
        default=TwirlingOptions(gates=True, measure=True, strategy="active-accum")
    )


@dataclass(frozen=True)
class _ResilienceLevel3Options:
    resilience_level: int = 3
    resilience: ResilienceOptions = field(
        default=ResilienceOptions(
            measure_noise_mitigation=True, zne_mitigation=False, **asdict(_PecOptions())
        )
    )
    twirling: TwirlingOptions = field(
        default=TwirlingOptions(gates=True, measure=True, strategy="active")
    )


_DEFAULT_RESILIENCE_LEVEL_OPTIONS = {
    0: _ResilienceLevel0Options(),
    1: _ResilienceLevel1Options(),
    2: _ResilienceLevel2Options(),
    3: _ResilienceLevel3Options(),
}
