# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Zero noise extrapolation mitigation options.."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import Field

from .base import BaseOptionsModel

ExtrapolatorType = Literal[
    "linear",
    "exponential",
    "double_exponential",
    "polynomial_degree_1",
    "polynomial_degree_2",
    "polynomial_degree_3",
    "polynomial_degree_4",
    "polynomial_degree_5",
    "polynomial_degree_6",
    "polynomial_degree_7",
    "fallback",
]

PEA_DEFAULT_NOISE_FACTORS = (1, 1.5, 2, 2.5, 3)
"""The values of ``noise_factors`` used by default when PEA is selected."""

ZNE_DEFAULT_NOISE_FACTORS = (1, 3, 5)
"""The values of ``noise_factors`` used by default when gate folding is selected."""


class ZneOptions(BaseOptionsModel):
    """Zero noise extrapolation mitigation options. This is only used by the V2 Estimator.

    .. note::

        Any V2 estimator is guaranteed to return data fields called ``evs`` and ``stds`` that
        report the desired expectation value estimates and errors, respectively.
        When ZNE options are enabled in the runtime estimator, additional data is returned.

        In particular, suppose an input pub has observable array shape ``obs_shape`` and parameter
        values shape ``par_shape``, with corresponding pub shape
        ``shape=np.broadcast_shapes(obs_shape, par_shape)``. Then the corresponding pub result will
        additionally contain:

        1. ``pub_result.data.evs_extrapolated`` and ``pub_result.data.stds_extrapolated``,
            both with shape ``(*shape, num_extrapolators, num_evaluation_points)``, where
            ``num_extrapolators`` is the length of the list of
            ``options.resilience.zne.extrapolators``, and ``num_evaluation_points`` is the length of
            the list ``options.resilience.extrapolated_noise_factors``. These values provide
            evaluations of every extrapolator at every specified noise extrapolation value.
        2. ``pub_result.data.evs_noise_factors``, ``pub_result.data.stds_noise_factors``, and
           ``ensemble_stds_noise_factors`` all have shape ``(*shape, num_noise_factors)`` where
           ``num_noise_factors`` is the length of ``options.resilience.zne.noise_factors``. These
           values provide raw expectation values, averaged over twirling if applicable,
           at each of the noise amplifications; you can base your own fitting routines off of these
           values. In the case of no twirling, both ``*stds*`` arrays will be equal, otherwise,
           ``stds_noise_factors`` is derived from the spread over twirling samples, whereas
           ``ensemble_stds_noise_factors`` assumes only shot noise and no drift.

        Technical note: for single observables with multiple basis terms it might turn out that
        multiple extrapolation methods are used in *the same* expectation value, for example, ``XX``
        gets linearly extrapolated but ``XY`` gets exponentially extrapolated in the observable
        ``{"XX": 0.5, "XY": 0.5}``. Let's call this a *heterogeneous fit*. The data from (2) is
        evaluated from heterogeneous fits by selecting the best fit for every individual distinct
        term, whereas data from (1) is evaluated from forced homogenous fits, one for each provided
        extrapolator. If your work requires a nuanced distinction in this regard, we presently
        recommend that you use single-term observables in addition to your multi-term observables.

    References:
        1. Z. Cai, *Multi-exponential error extrapolation and combining error mitigation techniques
           for NISQ applications*,
           `npj Quantum Inf 7, 80 (2021) <https://www.nature.com/articles/s41534-021-00404-3>`_
    """

    amplifier: Literal["gate_folding", "gate_folding_front", "gate_folding_back", "pea"] = (
        "gate_folding"
    )
    """Which technique to use for amplifying noise.

    One of:

        * `"gate_folding"` (default) uses 2-qubit gate folding to amplify noise. If the noise
            factor requires amplifying only a subset of the gates, then these gates are chosen
            randomly.
        * `"gate_folding_front"` uses 2-qubit gate folding to amplify noise. If the noise
            factor requires amplifying only a subset of the gates, then these gates are selected
            from the front of the topologically ordered DAG circuit.
        * `"gate_folding_back"` uses 2-qubit gate folding to amplify noise. If the noise
            factor requires amplifying only a subset of the gates, then these gates are selected
            from the back of the topologically ordered DAG circuit.
        * `"pea"` uses a technique called Probabilistic Error Amplification
            (`PEA <https://www.nature.com/articles/s41586-023-06096-3>`_) to amplify noise. When
            this option is selected, gate twirling will always be used whether or not it has
            been enabled in the options. In this technique, the twirled noise model of each each
            unique layer of entangling gates in your ISA circuits is learned beforehand, see
            :class:`~.LayerNoiseLearningOptions` for relevant learning options. Once complete,
            your circuits are executed at each noise factor, where every entangling layer of
            your circuits is amplified by probabilistically injecting single-qubit noise
            proportional to the corresponding learned noise model.
    """

    noise_factors: Sequence[Annotated[float, Field(ge=1)]] | Literal["auto"] = "auto"
    """ noise_factors: Noise factors to use for noise amplification.

    The default depends on the amplifier method - the default for pea is
    :class:.~PEA_DEFAULT_NOISE_FACTORS` and the default for the other methods
    is :class:.~ZNE_DEFAULT_NOISE_FACTORS`.
    """

    extrapolator: ExtrapolatorType | Sequence[ExtrapolatorType] = ("exponential", "linear")
    r"""Extrapolator(s) to try (in order) for extrapolating to zero noise.

    The available options are:

        * ``"exponential"``, which fits the data using an exponential decaying function
            defined as :math:`f(x; A, \tau) = A e^{-x/\tau}`, where :math:`A = f(0; A, \tau)`
            is the value at zero noise (:math:`x=0`) and :math:`\tau>0` is a positive rate.
        * ``"double_exponential"``, which uses a sum of two exponential as in Ref. 1.
        * ``"polynomial_degree_(1 <= k <= 7)"``, which uses a polynomial function defined as
            :math:`f(x; c_0, c_1, \ldots, c_k) = \sum_{i=0, k} c_i x^i`.
        * ``"linear"``, which is equivalent to ``"polynomial_degree_1"``.
        * ``"fallback"``, which simply returns the raw data corresponding to the lowest noise
            factor (typically ``1``) without performing any sort of extrapolation.

    The extrapolated values (``evs_extrapolated`` and ``stds_extrapolated``) are sorted
    according to the order of the provided extrapolators. If more than one extrapolator is
    specified, the ``evs`` and ``stds`` reported in the result's data refer to the first
    successful extrapolator, where an extrapolator success is determined heuristically.
    """

    extrapolated_noise_factors: Sequence[Annotated[float, Field(ge=0)]] | Literal["auto"] = "auto"
    r"""Noise factors to evaluate the fit extrapolation models at.

    If auto, the expectation values will be evaluated at ``[0, *noise_factors]``. This
    option does not affect execution or model fitting in any way, it only determines the
    points at which the ``extrapolator``\s are evaluated to be returned in the data
    fields called ``evs_extrapolated`` and ``stds_extrapolated``.
    """
