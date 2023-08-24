import logging
from typing import Any, Optional, Dict


logger = logging.getLogger(__name__)


def validate(options: dict[str, Any]) -> None:
    return _validate_qctrl_options(
        skip_transpilation=options.get('skip_transpilation', False),
        transpilation_settings=options.get('transpilation_settings'),
        resilience_settings=options.get('resilience_settings'))


def _validate_qctrl_options(
        skip_transpilation: bool,
        transpilation_settings: Optional[dict[str, Any]] = None,
        resilience_settings: Optional[dict[str, Any]] = None,
) -> None:
    """
    Validate options passed into the program.
    skip_transpilation : bool
        Whether transpilation should be skipped.
    transpilation_settings : Optional[dict[str, Any]], optional
        The transpilation settings, by default None.
    resilience_settings : Optional[dict[str, Any]], optional
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
                "The following settings cannot be customized "
                "and will be overwritten: %s",
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
            arguments={"unsupported_settings": ','.join(found_unsupported_keys)},
        )


def _check_argument(
        condition: bool,
        description: str,
        arguments: Dict[str, str],
) -> None:
    if not condition:
        error_str = f'{description} arguments={arguments}'
        raise ValueError(error_str)

