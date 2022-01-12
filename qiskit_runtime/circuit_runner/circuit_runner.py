# This code is part of qiskit-runtime.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Circuit-runner runtime program.

This is a simplified version of the circuit-runner program.
"""

from qiskit.compiler import transpile, schedule


def main(
    backend,
    user_messenger,  # pylint: disable=unused-argument
    circuits,
    initial_layout=None,
    seed_transpiler=None,
    optimization_level=None,
    transpiler_options=None,
    scheduling_method=None,
    schedule_circuit=False,
    inst_map=None,
    meas_map=None,
    measurement_error_mitigation=False,
    **kwargs,
):
    """Run the circuits on the backend."""

    # transpiling the circuits using given transpile options
    transpiler_options = transpiler_options or {}
    circuits = transpile(
        circuits,
        initial_layout=initial_layout,
        seed_transpiler=seed_transpiler,
        optimization_level=optimization_level,
        backend=backend,
        **transpiler_options,
    )

    if schedule_circuit:
        circuits = schedule(
            circuits=circuits,
            backend=backend,
            inst_map=inst_map,
            meas_map=meas_map,
            method=scheduling_method,
        )

    if not isinstance(circuits, list):
        circuits = [circuits]

    # Compute raw results
    result = backend.run(circuits, **kwargs).result()

    if measurement_error_mitigation:
        # Performs measurement error mitigation.
        pass

    return result.to_dict()
