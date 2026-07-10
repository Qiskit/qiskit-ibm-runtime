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

from typing import Annotated

from pydantic import InstanceOf
from qiskit.quantum_info import PauliLindbladMap

from .measure_noise_learning_options import MeasureNoiseLearningOptions
from .pec_options import PecOptions
from .utils import OptionsModel
from .zne_options import ZneOptions


class ResilienceOptions(OptionsModel):
    """Resilience options for V2 Estimator."""

    measure_mitigation: bool = True
    """Whether to enable measurement error mitigation method.

    If you enable measurement mitigation, you can fine-tune its noise learning
    by using :attr:`~measure_noise_learning`. See :class:`.~MeasureNoiseLearningOptions`
    for all measurement mitigation noise learning options.
    """

    measure_noise_learning: MeasureNoiseLearningOptions = MeasureNoiseLearningOptions()
    """Additional measurement noise learning options."""

    pec_mitigation: bool = False
    """Whether to turn on Probabilistic Error Cancellation error mitigation method.

    If you enable PEC, you can fine-tune its options by using :attr:`~pec`.
    See :class:`PecOptions` for additional PEC-related options.

    You must also provide a noise model via :attr:`~noise_model_mapping` when enabling PEC.
    """

    pec: PecOptions = PecOptions()
    """Additional probabalistic error cancellation mitigation options."""

    zne_mitigation: bool = False
    """Whether to turn on Zero Noise Extrapolation error mitigation method.

    If you enable ZNE, you can fine-tune its options by using :attr:`~zne`.
    See :class:`ZneOptions` for additional ZNE-related options.
    """

    zne: ZneOptions = ZneOptions()
    """Additional zero noise extrapolation mitigation options."""

    noise_model_mapping: dict[str, Annotated[PauliLindbladMap, InstanceOf]] | None = None
    """A noise model mapping for PEC mitigation.

    Maps layer references (strings) to :class:`~qiskit.quantum_info.PauliLindbladMap`
    objects that describe the noise characteristics of that layer. The dict contains
    layers from all PUBs. This is required when using PEC mitigation.
    """
