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

"""Utilities for experimental features"""

from typing import Callable, Any
import functools
import warnings

from qiskit_ibm_runtime.exceptions import IBMRuntimeExperimentalWarning


def _issue_experimental_msg(
    entity: str,
    since: str,
    package_name: str,
    additional_msg: str | None = None,
) -> str:
    """Construct a standardized experimental feature warning message."""
    msg = (
        f"{entity}, introduced in {package_name} on version {since}, "
        "is experimental and may change or be removed in the future."
    )
    if additional_msg:
        msg += f" {additional_msg}"
    return msg


def experimental_func(
    *,
    since: str,
    additional_msg: str | None = None,
    package_name: str = "qiskit-ibm-runtime",
    is_property: bool = False,
    stacklevel: int = 2,
) -> Callable:

    def decorator(func):
        qualname = func.__qualname__
        mod_name = func.__module__

        # Note: decorator must be placed AFTER @property decorator
        if is_property:
            entity = f"The property ``{mod_name}.{qualname}``"
        elif "." in qualname:
            if func.__name__ == "__init__":
                cls_name = qualname[: -len(".__init__")]
                entity = f"The class ``{mod_name}.{cls_name}``"
            else:
                entity = f"The method ``{mod_name}.{qualname}()``"
        else:
            entity = f"The function ``{mod_name}.{qualname}()``"

        msg = _issue_experimental_msg(entity, since, package_name, additional_msg)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(msg, category=IBMRuntimeExperimentalWarning, stacklevel=stacklevel)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def experimental_arg(
    name: str,
    *,
    since: str,
    additional_msg: str | None = None,
    description: str | None = None,
    package_name: str = "qiskit-ibm-runtime",
    predicate: Callable[[Any], bool] | None = None,
) -> Callable:
    def decorator(func):
        func_name = f"{func.__module__}.{func.__qualname__}()"
        entity = description or f"``{func_name}``'s argument ``{name}``"

        msg = _issue_experimental_msg(entity, since, package_name, additional_msg)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if name in kwargs:
                if predicate is None or predicate(kwargs[name]):
                    warnings.warn(msg, category=IBMRuntimeExperimentalWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
