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
from dataclasses import dataclass, asdict, fields, field
import copy

from ..utils.deprecation import issue_deprecation_msg
from ..runtime_options import RuntimeOptions
from .utils import _flexible, Dict
from .environment_options import EnvironmentOptions
from .execution_options import ExecutionOptions
from .simulator_options import SimulatorOptions
from .transpilation_options import TranspilationOptions


@_flexible
@dataclass
class Options:
    """Options for the primitive programs.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation times. This is based on the
            ``optimization_level`` parameter in qiskit-terra but may include
            backend-specific optimization.

            * 0: no optimization
            * 1: light optimization
            * 2: heavy optimization
            * 3: even heavier optimization

        resilience_level: How much resilience to build against errors.
            Higher levels generate more accurate results,
            at the expense of longer processing times.

            * 0: no resilience
            * 1: light resilience

        transpilation: Transpilation options. See :class:`TranspilationOptions` for all
            available options.

        execution: Execution time options. See :class:`ExecutionOptions` for all available options.

        environment: Options related to the execution environment. See
            :class:`EnvironmentOptions` for all available options.

        simulator: Simulator options. See
            :class:`SimulatorOptions` for all available options.
    """

    optimization_level: int = 1
    resilience_level: int = 0
    transpilation: Union[TranspilationOptions, Dict] = field(
        default_factory=TranspilationOptions
    )
    execution: Union[ExecutionOptions, Dict] = field(default_factory=ExecutionOptions)
    environment: Union[EnvironmentOptions, Dict] = field(
        default_factory=EnvironmentOptions
    )
    simulator: Union[SimulatorOptions, Dict] = field(default_factory=SimulatorOptions)

    _obj_fields: ClassVar[dict] = {
        "transpilation": TranspilationOptions,
        "execution": ExecutionOptions,
        "environment": EnvironmentOptions,
        "simulator": SimulatorOptions,
    }

    @classmethod
    def _from_dict(cls, data: dict) -> "Options":
        data = copy.copy(data)
        environ_dict = data.pop("environment", {})
        if "image" in data.keys():
            issue_deprecation_msg(
                msg="The 'image' option has been moved to the 'environment' category",
                version="0.7",
                remedy="Please specify 'environment':{'image': image} instead.",
            )
            environ_dict["image"] = data.pop("image")
        environment = EnvironmentOptions(**environ_dict)
        transp = TranspilationOptions(**data.pop("transpilation", {}))
        execution = ExecutionOptions(**data.pop("execution", {}))
        return cls(
            environment=environment,
            transpilation=transp,
            execution=execution,
            **data,
        )

    @staticmethod
    def _get_program_inputs(options: dict) -> dict:
        """Convert the input options to program compatible inputs.

        Returns:
            Inputs acceptable by primitive programs.
        """
        inputs = {}
        inputs["transpilation_settings"] = options.get("transpilation", {})
        inputs["transpilation_settings"].update(
            {"optimization_settings": {"level": options.get("optimization_level")}}
        )
        inputs["resilience_settings"] = {"level": options.get("resilience_level")}
        inputs["run_options"] = options.get("execution")
        inputs["run_options"].update(options.get("simulator"))

        known_keys = Options.__dataclass_fields__.keys()
        # Add additional unknown keys.
        for key in options.keys():
            if key not in known_keys:
                inputs[key] = options[key]
        return inputs

    @staticmethod
    def _get_runtime_options(options: dict) -> dict:
        """Extract runtime options.

        Returns:
            Runtime options.
        """
        # default_env = asdict(EnvironmentOptions())
        environment = options.get("environment") or {}
        out = {}

        for fld in fields(RuntimeOptions):
            if fld.name in environment:
                out[fld.name] = environment[fld.name]

        return out

    def _merge_options(self, new_options: Optional[dict] = None) -> dict:
        """Merge current options with the new ones.

        Args:
            new_options: New options to merge.

        Returns:
            Merged dictionary.
        """

        def _update_options(old: dict, new: dict) -> None:
            if not new:
                return
            for key, val in old.items():
                if key in new.keys():
                    old[key] = new.pop(key)
                if isinstance(val, dict):
                    _update_options(val, new)

        combined = asdict(self)
        # First update values of the same key.
        _update_options(combined, new_options)
        # Add new keys.
        for key, val in new_options.items():
            if key not in combined:
                combined[key] = val
        return combined
