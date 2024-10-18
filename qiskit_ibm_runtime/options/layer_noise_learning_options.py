# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Options for learning layer noise."""

from typing import Union, List

from pydantic import ValidationInfo, field_validator

from .utils import (
    Unset,
    UnsetType,
    primitive_dataclass,
    make_constraint_validator,
    skip_unset_validation,
)


@primitive_dataclass
class LayerNoiseLearningOptions:
    """Options for learning layer noise. This is only used by V2 Estimator.

    .. note::
        These options are only used when the resilience level or options specify a
        technique that requires layer noise learning.

    .. note::

        The total number of unique circuits implemented to learn the noise of a single layer
        depends solely on :attr:`~layer_pair_depths` and :attr:`~num_randomizations`. For example,
        if ``layer_pair_depths`` contains six depths and ``num_randomizations`` is set to ``32``,
        the noise learning stage executes a total of ``6 * 9`` unique circuits per layer, each
        one with ``32`` randomizations (at :attr:`~shots_per_randomization` each).

        The number ``9`` above is the number of unique circuits that need to be implemented to
        learn the noise for all the two-qubit subsystem in the given layer by performing local
        measurements. Indeed, learning the noise for a single one of these subsystems requires
        measuring all the ``16`` two-qubit Paulis on that subsystem. Taking advantage of
        commutation relations to measure more than one of these Paulis (for example, ``XI``,
        ``IX``, and ``XX``) with a single circuit, it is possible to measure all these ``16``
        Paulis by implementing only ``9`` circuits. Parallelizing these measurement tasks in the
        optimal way allows then measuring the ``16`` Paulis for all of the layer's two-qubit
        subsystems with only ``9`` circuits. More details in Ref. [1].

    References:
        1. E. van den Berg, Z. Minev, A. Kandala, K. Temme, *Probabilistic error
           cancellation with sparse Pauli–Lindblad models on noisy quantum processors*,
           Nature Physics volume 19, pages 1116–1121 (2023).
           `arXiv:2201.09866 [quant-ph] <https://arxiv.org/abs/2201.09866>`_

    """

    max_layers_to_learn: Union[UnsetType, int, None] = Unset
    r"""The max number of unique layers to learn.
        A ``None`` value indicates that there is no limit.
        If there are more unique layers present, then some layers will not be learned or
        mitigated. The learned layers are prioritized based on the number of times they
        occur in a set of run Estimator PUBs, and for equally occurring layers are
        further sorted by the number of two-qubit gates in the layer. 
        
        Default: 4.
    """
    shots_per_randomization: Union[UnsetType, int] = Unset
    r"""The total number of shots to use per random learning circuit.
        A learning circuit is a random circuit at a specific learning depth with a specific
        measurement basis that is executed on hardware. 
        
        Default: 128.
    """
    num_randomizations: Union[UnsetType, int] = Unset
    r"""The number of random circuits to use per learning circuit configuration.
        A configuration is a measurement basis and depth setting. For example, if your experiment
        has six depths, then setting this value to 32 will result in a total of ``32 * 9 * 6``
        circuits that need to be executed (where ``9`` is the number of circuits that need to be
        implemented to measure all the required observables, see the note in the docstring for
        :class:`~.LayerNoiseLearningOptions` for mode details), at :attr:`~shots_per_randomization`
        each. 
        
        Default: 32.
    """
    layer_pair_depths: Union[UnsetType, List[int]] = Unset
    r"""The circuit depths (measured in number of pairs) to use in learning
        experiments. Pairs are used as the unit because we exploit the order-2 nature of
        our entangling gates in the noise learning implementation. A value of ``3``
        would correspond to 6 layers of the layer of interest, for example.

        Default: (0, 1, 2, 4, 16, 32).
    """

    _ge0 = make_constraint_validator("max_layers_to_learn", ge=0)
    _ge1 = make_constraint_validator("shots_per_randomization", "num_randomizations", ge=1)

    @field_validator("layer_pair_depths", mode="after")
    @classmethod
    @skip_unset_validation
    def _nonnegative_list(cls, value: List[int], info: ValidationInfo) -> List[int]:
        if any(i < 0 for i in value):
            raise ValueError(f"`{cls.__name__}.{info.field_name}` option value must all be >= 0")
        return value
