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

from typing import Optional, Union, ClassVar
from dataclasses import dataclass, fields, field
import copy
import warnings

from qiskit.transpiler import CouplingMap

from .utils import Dict, _to_obj

from .environment_options import EnvironmentOptions
from .execution_options import ExecutionOptions
from .simulator_options import SimulatorOptions
from .transpilation_options import TranspilationOptions
from .resilience_options import ResilienceOptions
from ..runtime_options import RuntimeOptions


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
            <https://docs.quantum.ibm.com/run/configure-error-mitigation>`_.
            for more information about the error mitigation methods used at each level.

        max_execution_time: Maximum execution time in seconds, which is based
            on system execution time (not wall clock time). System execution time is
            the amount of time that the system is dedicated to processing your job.
            If a job exceeds this time limit, it is forcibly cancelled.
            Simulator jobs continue to use wall clock time.

            Refer to the
            `Max execution time documentation
            <https://docs.quantum.ibm.com/run/max-execution-time>`_.
            for more information.

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
    _DEFAULT_RESILIENCE_LEVEL = 1
    _MAX_OPTIMIZATION_LEVEL = 3
    _MAX_RESILIENCE_LEVEL_ESTIMATOR = 3
    _MAX_RESILIENCE_LEVEL_SAMPLER = 1
    _MAX_EXECUTION_TIME = 8 * 60 * 60  # 8 hours for real device

    optimization_level: Optional[int] = None
    resilience_level: Optional[int] = None
    max_execution_time: Optional[int] = None
    transpilation: Union[TranspilationOptions, Dict] = field(default_factory=TranspilationOptions)
    resilience: Union[ResilienceOptions, Dict] = field(default_factory=ResilienceOptions)
    execution: Union[ExecutionOptions, Dict] = field(default_factory=ExecutionOptions)
    environment: Union[EnvironmentOptions, Dict] = field(default_factory=EnvironmentOptions)
    simulator: Union[SimulatorOptions, Dict] = field(default_factory=SimulatorOptions)

    _obj_fields: ClassVar[dict] = {
        "transpilation": TranspilationOptions,
        "execution": ExecutionOptions,
        "environment": EnvironmentOptions,
        "simulator": SimulatorOptions,
        "resilience": ResilienceOptions,
    }

    def __post_init__(self):  # type: ignore
        """Convert dictionary fields to object."""
        obj_fields = getattr(self, "_obj_fields", {})
        for key in list(obj_fields):
            if hasattr(self, key):
                orig_val = getattr(self, key)
                setattr(self, key, _to_obj(obj_fields[key], orig_val))

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitives.
        """
        sim_options = options.get("simulator", {})
        inputs = {}
        inputs["transpilation_settings"] = options.get("transpilation", {})
        inputs["transpilation_settings"].update(
            {
                "optimization_settings": {"level": options.get("optimization_level")},
                "coupling_map": sim_options.get("coupling_map", None),
                "basis_gates": sim_options.get("basis_gates", None),
            }
        )
        if isinstance(inputs["transpilation_settings"]["coupling_map"], CouplingMap):
            inputs["transpilation_settings"]["coupling_map"] = list(
                map(list, inputs["transpilation_settings"]["coupling_map"].get_edges())
            )

        inputs["resilience_settings"] = options.get("resilience", {})
        inputs["resilience_settings"].update({"level": options.get("resilience_level")})
        inputs["run_options"] = options.get("execution")
        inputs["run_options"].update(
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
        ResilienceOptions.validate_resilience_options(options.get("resilience"))
        TranspilationOptions.validate_transpilation_options(options.get("transpilation"))
        execution_time = options.get("max_execution_time")
        if execution_time is not None:
            if execution_time > Options._MAX_EXECUTION_TIME:
                raise ValueError(
                    f"max_execution_time must be below " f"{Options._MAX_EXECUTION_TIME} seconds."
                )

        EnvironmentOptions.validate_environment_options(options.get("environment"))
        ExecutionOptions.validate_execution_options(options.get("execution"))
        SimulatorOptions.validate_simulator_options(options.get("simulator"))

    @staticmethod
    def _remove_none_values(options: dict) -> dict:
        """Remove `None` values from the options dictionary."""
        new_options = {}
        for key, value in options.items():
            if value is not None:
                if isinstance(value, dict):
                    new_suboptions = {}
                    for subkey, subvalue in value.items():
                        if subvalue is not None:
                            new_suboptions[subkey] = subvalue
                    new_options[key] = new_suboptions
                else:
                    new_options[key] = value

        return new_options

    @staticmethod
    def _set_default_resilience_options(options: dict) -> dict:
        """Set default resilience options for resilience level 2."""
        if options["resilience_level"] == 2:
            if not options["resilience"]["noise_factors"]:
                options["resilience"]["noise_factors"] = (1, 3, 5)
            if not options["resilience"]["extrapolator"]:
                options["resilience"]["extrapolator"] = "LinearExtrapolator"

        return options

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
                    old[key] = new.pop(key)
                elif key in matched.keys():
                    old[key] = matched.pop(key)

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
