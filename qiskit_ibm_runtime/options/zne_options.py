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
from typing import Literal

from pydantic import field_validator, model_validator

from .utils import Unset, UnsetType, primitive_dataclass, skip_unset_validation

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


@primitive_dataclass
class ZneOptions:
    r"""Zero noise extrapolation mitigation options. This is only used by the V2 Estimator.

    .. note::

        Any V2 estimator returns data fields called ``evs`` and ``stds`` in ``pub_result.data`` that
        report the desired expectation value estimates and uncertainties, respectively.
        When ZNE options are enabled in the runtime estimator, additional noise-factor and
        extrapolation data fields are returned in ``pub_result.data``.

        In particular, suppose an input pub has observable array shape ``obs_shape`` and parameter
        values shape ``par_shape``, with corresponding pub shape
        ``shape=np.broadcast_shapes(obs_shape, par_shape)``. Then the result data fields are:

        1. ``pub_result.data.evs``: Zero-noise extrapolated expectation values evaluated at
           :math:`\lambda = 0`. For multi-term observables, this is evaluated via a *heterogeneous fit*
           by selecting the best-fitting model independently for each distinct Pauli term.
           Shape: ``shape``.
        2. ``pub_result.data.stds``: Propagated standard error corresponding to ``evs``.
           Shape: ``shape``.
        3. ``pub_result.data.evs_noise_factors``: Raw (non-extrapolated) expectation values measured
           at each noise amplification scale factor, averaged over all shots and twirling randomizations.
           Shape: ``(*shape, num_noise_factors)``, where ``num_noise_factors`` is the length of
           ``options.resilience.zne.noise_factors``.
        4. ``pub_result.data.stds_noise_factors``: Empirical standard error of the mean across twirling
           randomizations at each noise factor. When twirling is enabled, this reflects hardware drift
           and noise variations between randomized circuits in addition to shot noise.
           Shape: ``(*shape, num_noise_factors)``.
        5. ``pub_result.data.ensemble_stds_noise_factors``: Theoretical shot-noise standard error at
           each noise factor under the i.i.d. shot-noise assumption (pooling all shots as one ensemble).
           Shape: ``(*shape, num_noise_factors)``.
        6. ``pub_result.data.evs_extrapolated``: Expectation values from each candidate extrapolator
           model, evaluated at every noise factor point in
           ``options.resilience.zne.extrapolated_noise_factors`` (defaulting to ``[0, *noise_factors]``).
           These are forced *homogeneous fits*—one fit per candidate extrapolator applied to all terms—allowing
           direct comparison of candidate models.
           Shape: ``(*shape, num_extrapolators, num_evaluation_points)``, where ``num_extrapolators``
           is the length of ``options.resilience.zne.extrapolator`` and ``num_evaluation_points`` is
           the length of ``options.resilience.zne.extrapolated_noise_factors``.
        7. ``pub_result.data.stds_extrapolated``: Propagated standard errors corresponding to
           ``evs_extrapolated``, evaluated at each point in ``extrapolated_noise_factors``.
           Shape: ``(*shape, num_extrapolators, num_evaluation_points)``.

        **Extrapolation Failure and Fallback**:

        * If a candidate model fails to fit (e.g. non-convergence or singular covariance),
          the heuristic advances to the next candidate model in the ordered ``extrapolator`` list.
        * If ``"fallback"`` is included in ``extrapolator`` and all prior models fail, the
          estimator returns the raw data from the lowest evaluated noise factor without extrapolation.
        * In ``evs_extrapolated`` and ``stds_extrapolated``, candidate models that fail to fit evaluate
          to ``NaN`` (``numpy.nan``).
        * If all candidate models fail and ``"fallback"`` is not specified, the candidate with the smallest
          standard error is chosen (evaluating to ``inf`` if all models failed).
        * The raw measurement fields (``evs_noise_factors``, ``stds_noise_factors``, and
          ``ensemble_stds_noise_factors``) are **always** populated and returned regardless of whether
          extrapolation succeeds.

        For in-depth explanations, statistical formulas, and workflow diagrams, see
        :mod:`qiskit_ibm_runtime.executor_estimator`.

    References:
        1. Z. Cai, *Multi-exponential error extrapolation and combining error mitigation techniques
           for NISQ applications*,
           `npj Quantum Inf 7, 80 (2021) <https://www.nature.com/articles/s41534-021-00404-3>`_
    """

    amplifier: (
        UnsetType | Literal["gate_folding", "gate_folding_front", "gate_folding_back", "pea"]
    ) = Unset
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

    noise_factors: UnsetType | Sequence[float] = Unset
    """ noise_factors: Noise factors to use for noise amplification.

    Default: ``(1, 3, 5)``.
    """

    extrapolator: UnsetType | ExtrapolatorType | Sequence[ExtrapolatorType] = Unset
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

    Default: ``("exponential", "linear")``.
    """

    extrapolated_noise_factors: UnsetType | Sequence[float] = Unset
    r"""Noise factors to evaluate the fit extrapolation models at.

    If unset, this will default to ``[0, *noise_factors]``. This
    option does not affect execution or model fitting in any way, it only determines the
    points at which the ``extrapolator``\s are evaluated to be returned in the data
    fields called ``evs_extrapolated`` and ``stds_extrapolated``.
    """

    def _default_noise_factors(self) -> Sequence[float]:
        return (1, 3, 5)

    @classmethod
    def _default_extrapolator(cls) -> Sequence[ExtrapolatorType]:
        return ("exponential", "linear")

    @field_validator("noise_factors")
    @classmethod
    @skip_unset_validation
    def _validate_zne_noise_factors(cls, factors: Sequence[float]) -> Sequence[float]:
        """Validate noise_factors."""
        if any(i < 1 for i in factors):
            raise ValueError("noise_factors` option value must all be >= 1")
        return factors

    @model_validator(mode="after")
    def _validate_options(self) -> ZneOptions:
        """Check that there are enough noise factors for all extrapolators."""
        noise_factors = (
            self.noise_factors if self.noise_factors != Unset else self._default_noise_factors()
        )
        extrapolator = (
            self.extrapolator if self.extrapolator != Unset else self._default_extrapolator()
        )

        required_factors = {
            "linear": 2,
            "exponential": 2,
            "double_exponential": 4,
            "fallback": 2,
        }
        for idx in range(1, 8):
            required_factors[f"polynomial_degree_{idx}"] = idx + 1

        extrapolators: Sequence = (
            [extrapolator]  # type: ignore[assignment]
            if isinstance(extrapolator, str)
            else extrapolator
        )
        for extrap in extrapolators:
            if len(noise_factors) < required_factors[extrap]:  # type: ignore[arg-type]
                raise ValueError(
                    f"{extrap} requires at least {required_factors[extrap]} noise_factors"
                )
        return self
