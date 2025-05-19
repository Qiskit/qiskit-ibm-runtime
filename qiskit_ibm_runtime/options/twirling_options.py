# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Twirling options."""

from typing import Literal, Union

from .utils import Unset, UnsetType, primitive_dataclass, make_constraint_validator


TwirlingStrategyType = Literal[
    "active",
    "active-accum",
    "active-circuit",
    "all",
]


@primitive_dataclass
class TwirlingOptions:
    """Twirling options."""

    enable_gates: Union[UnsetType, bool] = Unset
    r"""Whether to apply 2-qubit Clifford gate twirling.
    
    Default: ``False``.
    """

    enable_measure: Union[UnsetType, bool] = Unset
    r"""Whether to enable twirling to measurement instructions, as long as the measurement is not 
    involved within a conditional block.

    Default: ``True`` for ``Estimator``, ``False`` for ``Sampler``.
    """

    num_randomizations: Union[UnsetType, int, Literal["auto"]] = Unset
    r"""The number of random samples to use when twirling or peforming sampled mitigation.

    If ``num_randomizations`` is "auto", for every pub executed ``shots`` times:

      * If ``shots_per_randomization`` is also "auto", ``shots_per_randomization`` is set first
        as described below, then ``num_randomizations`` is set as
        ``ceil(shots/shots_per_randomization)``, where ``ceil`` is the ceiling function.
      * Otherwise, the value is set to ``ceil(shots/shots_per_randomization)``.

      Default: ``"auto"``.

    .. note::
      The ``shots`` value specified in a PUB or in the ``run()`` method is considered part of the
      primitive execution interface and therefore is always obeyed. ``default_shots``, on the other hand,
      is considered a Qiskit Runtime specific option. Therefore, the product of
      ``num_randomizations`` and ``shots_per_randomization`` takes precedence over ``default_shots``.
    """

    shots_per_randomization: Union[UnsetType, int, Literal["auto"]] = Unset
    r"""The number of shots to run for each random sample.

    If "auto", for every pub executed ``shots`` times:

      * If ``num_randomizations`` is also "auto", the value is set to ``64`` for PEC mitigation
        or to ``max(64, ceil(shots / 32))`` in all other cases, where ``ceil`` is the ceiling
        function.
      * Otherwise, the value is set to ``ceil(shots/num_randomizations)``.

      Default: ``"auto"``.

    .. note::
      The ``shots`` value specified in a PUB or in the ``run()`` method is considered part of the
      primitive execution interface and therefore is always obeyed. ``default_shots``, on the other hand,
      is considered a Qiskit Runtime specific option. Therefore, the product of
      ``num_randomizations`` and ``shots_per_randomization`` takes precedence over ``default_shots``.
    """

    strategy: Union[UnsetType, TwirlingStrategyType] = Unset
    r"""Specify the strategy of twirling qubits in identified layers of 2-qubit twirled gates.

    Allowed values are:

      * If ``"active"`` only the instruction qubits in each individual twirled
        layer will be twirled.
      * If ``"active-circuit"`` the union of all instruction qubits in the circuit
        will be twirled in each twirled layer.
      * If ``"active-accum"`` the union of instructions qubits in the circuit up to
        the current twirled layer will be twirled in each individual twirled layer.
      * If ``"all"`` all qubits in the input circuit will be twirled in each
        twirled layer.

      Default: ``"active-accum"``.

    .. image:: /source_images/twirling_strategy_options.png
      :alt: Image illustrating the differences among twirling strategies. If "active", only
            instruction qubits in each layer will be twirled. If "active-circuit", 
            all instruction qubits in the circuit will be twirled. If "active-accum", the union 
            all instruction qubits in the circuit up to the current twirled layer will be twirled. 
            Finally, if "all", all qubits in the input circuit will be twirled in each twirled layer.
    """

    _ge1 = make_constraint_validator("num_randomizations", "shots_per_randomization", ge=1)
