# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qctrl validation functions and helpers."""

import logging
from typing import Any, Optional, Dict

from ..options import Options
from ..options import EnvironmentOptions, ExecutionOptions, TranspilationOptions, SimulatorOptions

logger = logging.getLogger(__name__)


def validate(options: Dict[str, Any]) -> None:
    """Validates the runtime options for qctrl"""
    transpilation_settings = _copy_keys_with_values(options.get("transpilation", {}))
    transpilation_settings["optimization_level"] = options.get("optimization_level")

    resilience_settings = _copy_keys_with_values(options.get("resilience"))
    resilience_settings["level"] = options.get("resilience_level")

    # Validate the options with qctrl logic first.
    _validate_qctrl_options(
        skip_transpilation=transpilation_settings.get("skip_transpilation", False),
        transpilation_settings=transpilation_settings,
        resilience_settings=resilience_settings,
    )

    # Default validation otherwise.
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


def _copy_keys_with_values(settings: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in settings.items() if value}


def _validate_qctrl_options(
    skip_transpilation: bool,
    transpilation_settings: Optional[Dict[str, Any]] = None,
    resilience_settings: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Validate options passed into the program.
    skip_transpilation : bool
        Whether transpilation should be skipped.
    transpilation_settings : Optional[Dict[str, Any]], optional
        The transpilation settings, by default None.
    resilience_settings : Optional[Dict[str, Any]], optional
        The resilience settings, by default None.
    """
    _check_argument(
        skip_transpilation is False,
        description="Q-CTRL Primitives cannot skip transpilation.",
        arguments={},
    )

    # transpilation_settings
    if transpilation_settings is not None:
        default_transpilation_values = {
            "optimization_level": 3,
            "approximation_degree": 0,
        }
        different_keys = [
            key
            for key, value in default_transpilation_values.items()
            if key in transpilation_settings and value != transpilation_settings[key]
        ]

        if different_keys:
            logger.warning(
                "The following settings cannot be customized and will be overwritten: %s",
                different_keys,
            )

        transpilation_settings.update(default_transpilation_values)

    if resilience_settings is not None:
        # Error when resilience_level different than 1
        resilience_level = resilience_settings.get("level", 1)

        _check_argument(
            resilience_level == 1,
            description="Q-CTRL Primitives do not support custom resilience level",
            arguments={"level": resilience_level},
        )
        # Error on extra resilience options
        unsupported_resilience_settings = {
            "noise_amplifier",
            "noise_factors",
            "extrapolator",
        }
        found_unsupported_keys = [
            key for key in unsupported_resilience_settings if key in resilience_settings
        ]
        _check_argument(
            found_unsupported_keys == [],
            description="Q-CTRL Primitives do not support certain resilience settings",
            arguments={"unsupported_settings": ",".join(sorted(found_unsupported_keys))},
        )


def _check_argument(
    condition: bool,
    description: str,
    arguments: Dict[str, str],
) -> None:
    if not condition:
        error_str = f"{description} arguments={arguments}"
        raise ValueError(error_str)
