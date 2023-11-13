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

"""Execution options."""

from dataclasses import dataclass
from typing import Literal, get_args, Optional
from numbers import Integral


ExecutionSupportedOptions = Literal[
    "shots",
    "init_qubits",
    "samples",
    "shots_per_sample",
    "interleave_samples",
]


@dataclass
class ExecutionOptions:
    """Execution options.

    Args:
        shots: Number of repetitions of each circuit, for sampling. Default: 4096.

        init_qubits: Whether to reset the qubits to the ground state for each shot.
            Default: ``True``.

        samples: The number of samples of each measurement circuit to run. This
            is used when twirling or resilience levels 1, 2, 3. If None it will
            be calculated automatically based on the ``shots`` and
            ``shots_per_sample`` (if specified).
            Default: None

        shots_per_sample: The number of shots per sample of each measurement
            circuit to run. This is used when twirling or resilience levels 1, 2, 3.
            If None it will be calculated automatically based on the ``shots`` and
            ``samples`` (if specified).
            Default: None

        interleave_samples: If True interleave samples from different measurement
            circuits when running. If False run all samples from each measurement
            circuit in order.
            Default: False
    """

    shots: int = 4096
    init_qubits: bool = True
    samples: Optional[int] = None
    shots_per_sample: Optional[int] = None
    interleave_samples: bool = False

    @staticmethod
    def validate_execution_options(execution_options: dict) -> None:
        """Validate that execution options are legal.
        Raises:
            ValueError: if any execution option is not supported
        """
        for opt in execution_options:
            if not opt in get_args(ExecutionSupportedOptions):
                raise ValueError(f"Unsupported value '{opt}' for execution.")

        shots = execution_options.get("shots")
        samples = execution_options.get("samples")
        shots_per_sample = execution_options.get("shots_per_sample")
        if (
            shots is not None
            and samples is not None
            and shots_per_sample is not None
            and shots != samples * shots_per_sample
        ):
            raise ValueError(
                f"If shots ({shots}) != samples ({samples}) * shots_per_sample ({shots_per_sample})"
            )
        if shots is not None:
            if not isinstance(shots, Integral):
                raise ValueError(f"shots must be None or an integer, not {type(shots)}")
            if shots < 0:
                raise ValueError("shots must be None or >= 1")
        if samples is not None:
            if not isinstance(samples, Integral):
                raise ValueError(f"samples must be None or an integer, not {type(samples)}")
            if samples < 0:
                raise ValueError("samples must be None or >= 1")
        if shots_per_sample is not None:
            if not isinstance(shots_per_sample, Integral):
                raise ValueError(
                    f"shots_per_sample must be None or an integer, not {type(shots_per_sample)}"
                )
            if shots_per_sample < 0:
                raise ValueError("shots_per_sample must be None or >= 1")
