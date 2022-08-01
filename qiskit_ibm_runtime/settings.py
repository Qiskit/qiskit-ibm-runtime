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

"""Primitive settings."""

from dataclasses import dataclass

@dataclass
class Transpilation:
    """Transpilation settings.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation times.

            * 0: no optimization
            * 1: light optimization
            * 2: heavy optimization
            * 3: even heavier optimization

        skip_transpilation: Whether to skip transpilation.

        inst_map: Mapping of unrolled gates to pulse schedules. If this is not provided,
            transpiler tries to get from the backend. If any user defined calibration
            is found in the map and this is used in a circuit, transpiler attaches
            the custom gate definition to the circuit. This enables one to flexibly
            override the low-level instruction implementation. This feature is available
            iff the backend supports the pulse gate experiment.

        initial_layout: Initial position of virtual qubits on physical qubits.
            See :function:`qiskit.compiler.transpile` for more information.

        layout_method: Name of layout selection pass ('trivial', 'dense', 'noise_adaptive', 'sabre')

        routing_method: Name of routing pass ('basic', 'lookahead', 'stochastic', 'sabre', 'none')

        translation_method: Name of translation pass ('unroller', 'translator', 'synthesis')

        scheduling_method: Name of scheduling pass.
            * ``'as_soon_as_possible'``: Schedule instructions greedily, as early as possible
            on a qubit resource. (alias: ``'asap'``)
            * ``'as_late_as_possible'``: Schedule instructions late, i.e. keeping qubits
            in the ground state when possible. (alias: ``'alap'``)
            If ``None``, no scheduling will be done.

        instruction_durations: Durations of instructions.
            Applicable only if scheduling_method is specified.
            The gate lengths defined in ``backend.properties`` are used as default.
            They are overwritten if this ``instruction_durations`` is specified.
            The format of ``instruction_durations`` must be as follows.
            The `instruction_durations` must be given as a list of tuples
            [(instruction_name, qubits, duration, unit), ...].
            | [('cx', [0, 1], 12.3, 'ns'), ('u3', [0], 4.56, 'ns')]
            | [('cx', [0, 1], 1000), ('u3', [0], 300)]
            If unit is omitted, the default is 'dt', which is a sample time depending on backend.
            If the time unit is 'dt', the duration must be an integer.

        approximation_degree (float): heuristic dial used for circuit approximation
            (1.0=no approximation, 0.0=maximal approximation)

        timing_constraints: An optional control hardware restriction on instruction time resolution.
            A quantum computer backend may report a set of restrictions, namely:

            - granularity: An integer value representing minimum pulse gate
              resolution in units of ``dt``. A user-defined pulse gate should have
              duration of a multiple of this granularity value.
            - min_length: An integer value representing minimum pulse gate
              length in units of ``dt``. A user-defined pulse gate should be longer
              than this length.
            - pulse_alignment: An integer value representing a time resolution of gate
              instruction starting time. Gate instruction should start at time which
              is a multiple of the alignment value.
            - acquire_alignment: An integer value representing a time resolution of measure
              instruction starting time. Measure instruction should start at time which
              is a multiple of the alignment value.

            This information will be provided by the backend configuration.
            If the backend doesn't have any restriction on the instruction time allocation,
            then ``timing_constraints`` is None and no adjustment will be performed.

        seed_transpiler: Sets random seed for the stochastic parts of the transpiler

        unitary_synthesis_method (str): The name of the unitary synthesis
            method to use. By default 'default' is used, which is the only
            method included with qiskit. If you have installed any unitary
            synthesis plugins you can use the name exported by the plugin.

        unitary_synthesis_plugin_config: An optional configuration dictionary
            that will be passed directly to the unitary synthesis plugin. By
            default this setting will have no effect as the default unitary
            synthesis method does not take custom configuration. This should
            only be necessary when a unitary synthesis plugin is specified with
            the ``unitary_synthesis`` argument. As this is custom for each
            unitary synthesis plugin refer to the plugin documentation for how
            to use this option.
    """

    # TODO: Add the other transpilation settings.

    optimization_level: int = 1
    skip_transpilation: bool = False

@dataclass
class Resilience:
    """Resilience settings.

    Args:
        level: How much resilience to build against errors.
            Higher levels generate more accurate results,
            at the expense of longer processing times.
            * 0: no resilience
            * 1: light resilience
    """
    level: int = 0
