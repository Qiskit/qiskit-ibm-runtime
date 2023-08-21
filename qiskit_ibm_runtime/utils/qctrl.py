from typing import Any, Optional


def validate_qctrl_options(options: dict[str, Any]) -> None:
    return _validate_qctr_options(
        skip_transpilation=options.get('skip_transpilation', False),
        transpilation_settings=options.get('transpilation_settings'),
        resilience_settings=options.get('resilience_settings'))

def _validate_qctr_options(
        skip_transpilation: bool,
        transpilation_settings: Optional[dict[str, Any]] = None,
        resilience_settings: Optional[dict[str, Any]] = None,
) -> None:
    # TODO
    raise NotImplementedError
