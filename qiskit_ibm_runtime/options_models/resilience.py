# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Resilience options."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import field_validator
from qiskit.circuit import BoxOp

from .base import BaseOptionsModel
from .measure_noise_learning import MeasureNoiseLearningOptions
from .pec import PecOptions
from .simulator import LayerNoiseModel
from .zne import ZneOptions


class ResilienceOptions(BaseOptionsModel):
    """Resilience options for V2 Estimator."""

    measure_mitigation: bool | None = None
    """Whether to enable measurement error mitigation method.

    If you enable measurement mitigation, you can fine-tune its noise learning by using
    :attr:`~measure_noise_learning`. See :class:`~.MeasureNoiseLearningOptions` for all measurement
    mitigation noise learning options.

    If ``measure_mitigation`` is ``None``, it is determined by the according to the resilience
    level: it is ``False`` for resilience level ``0``, and ``True`` for resilience levels ``1`` and
    ``2``.
    """

    measure_noise_learning: MeasureNoiseLearningOptions = MeasureNoiseLearningOptions()
    """Additional measurement noise learning options."""

    pec_mitigation: bool = False
    """Whether to turn on Probabilistic Error Cancellation error mitigation method.

    If you enable PEC, you can fine-tune its options by using :attr:`~pec`. See
    :class:`PecOptions` for additional PEC-related options.

    You must also provide a noise model via :attr:`~noise_model` when enabling PEC.
    """

    pec: PecOptions = PecOptions()
    """Additional probabalistic error cancellation mitigation options."""

    zne_mitigation: bool | None = None
    """Whether to turn on Zero-Noise Extrapolation error mitigation method.

    If you enable ZNE, you can fine-tune its options by using :attr:`~zne`. See
    :class:`~.ZneOptions` for additional ZNE related options.

    If ``zne_mitigation`` is left as ``None``, it inherits the default for the configured
    :attr:`~.EstimatorOptions.resilience_level`: ``False`` for resilience levels ``0`` and ``1``,
    and ``True`` for resilience level ``2``.
    """

    zne: ZneOptions = ZneOptions()
    """Additional zero noise extrapolation mitigation options."""

    layer_noise_model: Sequence[LayerNoiseModel] | None = None
    """Noise model specified by a collection of instructions and the noise that affects them."""

    @field_validator("layer_noise_model", mode="after")
    @classmethod
    def _validate_layer_noise_model(
        cls, value: Sequence[LayerNoiseModel] | None
    ) -> Sequence[LayerNoiseModel] | None:
        if value:
            for instruction, noise in value:
                if not isinstance(instruction.operation, BoxOp):
                    raise ValueError("Found an instruction that does not contain a box.")
                if len(instruction.qubits) != noise.num_qubits:
                    raise ValueError(
                        f"Found instruction with {len(instruction.qubits)}",
                        f"qubits but a noise model with {noise.num_qubits}.",
                    )
        return value
