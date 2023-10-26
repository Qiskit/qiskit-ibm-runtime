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

"""Utility functions for options."""

from ..ibm_backend import IBMBackend


def set_default_error_levels(
    options: dict,
    backend: IBMBackend,
    default_optimization_level: int,
    default_resilience_level: int,
) -> dict:
    """Set default resilience and optimization levels.

    Args:
        options: user passed in options.
        backend: backend the job will run on.
        default_optimization_level: the default optimization level from the options class
        default_resilience_level: the default resilience level from the options class

    Returns:
        options with correct error level defaults.
    """
    if options.get("optimization_level") is None:
        if (
            backend.configuration().simulator
            and options.get("simulator", {}).get("noise_model") is None
        ):
            options["optimization_level"] = 1
        else:
            options["optimization_level"] = default_optimization_level

    if options.get("resilience_level") is None:
        if (
            backend.configuration().simulator
            and options.get("simulator", {}).get("noise_model") is None
        ):
            options["resilience_level"] = 0
        else:
            options["resilience_level"] = default_resilience_level
    return options


def _to_obj(cls_, data):  # type: ignore
    if data is None:
        return cls_()
    if isinstance(data, cls_):
        return data
    if isinstance(data, dict):
        return cls_(**data)
    raise TypeError(
        f"{data} has an unspported type {type(data)}. It can only be {cls_} or a dictionary."
    )


class Dict:
    """Fake Dict type.

    This class is used to show dictionary as an acceptable type in docs without
    attaching all the dictionary attributes in Jupyter's auto-complete.
    """

    pass
