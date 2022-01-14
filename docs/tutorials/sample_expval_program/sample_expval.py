import mthree
from qiskit import transpile

# The entrypoint for our Runtime Program
def main(
    backend,
    user_messenger,
    circuits,
    expectation_operators="",
    shots=8192,
    transpiler_config={},
    run_config={},
    skip_transpilation=False,
    return_stddev=False,
    use_measurement_mitigation=False,
):

    """Compute expectation values for a list of operators after
    executing a list of circuits on the target backend.

    Parameters:
        backend (ProgramBackend): Qiskit backend instance.
        user_messenger (UserMessenger): Used to communicate with the program user.
        circuits: (QuantumCircuit or list): A single list of QuantumCircuits.
        expectation_operators (str or dict or list): Expectation values to evaluate.
        shots (int): Number of shots to take per circuit.
        transpiler_config (dict): A collection of kwargs passed to transpile().
        run_config (dict): A collection of kwargs passed to backend.run().
        skip_transpilation (bool): Skip transpiling of circuits, default=False.
        return_stddev (bool): Return upper bound on standard devitation,
                              default=False.
        use_measurement_mitigation (bool): Improve resulting using measurement
                                           error mitigation, default=False.

    Returns:
        array_like: Returns array of expectation values or a list of (expval, stddev)
                    tuples if return_stddev=True.
    """

    # transpiling the circuits using given transpile options
    if not skip_transpilation:
        trans_circuits = transpile(circuits, backend=backend, **transpiler_config)

        if not isinstance(trans_circuits, list):
            trans_circuits = [trans_circuits]
    # If skipping set circuits -> trans_circuits
    else:
        if not isinstance(circuits, list):
            trans_circuits = [circuits]
        else:
            trans_circuits = circuits

    # If we are given a single circuit but requesting multiple expectation values
    # Then set flag to make multiple pointers to same result.
    duplicate_results = False
    if isinstance(expectation_operators, list):
        if len(expectation_operators) and len(trans_circuits) == 1:
            duplicate_results = True

    if use_measurement_mitigation:
        # Get an the measurement mappings at end of circuits
        meas_maps = mthree.utils.final_measurement_mapping(trans_circuits)
        # Get an M3 mitigator
        mit = mthree.M3Mitigation(backend)
        # Calibrate over the set of qubits measured in the transpiled circuits.
        mit.cals_from_system(meas_maps)

    # Compute raw results
    result = backend.run(trans_circuits, shots=shots, **run_config).result()
    raw_counts = result.get_counts()

    # When using measurement mitigation we need to apply the correction and then
    # compute the expectation values from the computed quasi-probabilities.
    if use_measurement_mitigation:
        quasi_dists = mit.apply_correction(
            raw_counts, meas_maps, return_mitigation_overhead=return_stddev
        )

        if duplicate_results:
            quasi_dists = mthree.classes.QuasiCollection(
                [quasi_dists] * len(expectation_operators)
            )
        # There are two different calls depending on what we want returned.
        if return_stddev:
            return quasi_dists.expval_and_stddev(expectation_operators)
        return quasi_dists.expval(expectation_operators)

    # If the program didn't return in the mitigation loop above it means
    # we are processing the raw_counts data.  We do so here using the
    # mthree utilities
    if duplicate_results:
        raw_counts = [raw_counts] * len(expectation_operators)
    if return_stddev:
        return mthree.utils.expval_and_stddev(raw_counts, expectation_operators)
    return mthree.utils.expval(raw_counts, expectation_operators)
