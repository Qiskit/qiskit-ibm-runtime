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

# Grab functions and modules from dependencies
import numpy as np
import scipy.optimize as opt
from scipy.optimize import OptimizeResult
import mthree

# Grab functions and modules from Qiskit needed
from qiskit import QuantumCircuit, transpile
import qiskit.circuit.library.n_local as lib_local


# The entrypoint for our Runtime Program
def main(
    backend,
    user_messenger,
    hamiltonian,
    ansatz="EfficientSU2",
    ansatz_config={},
    x0=None,
    optimizer="SPSA",
    optimizer_config={"maxiter": 100},
    shots=8192,
    use_measurement_mitigation=False,
):

    """
    The main sample VQE program.

    Parameters:
        backend (ProgramBackend): Qiskit backend instance.
        user_messenger (UserMessenger): Used to communicate with the program user.
        hamiltonian (list): Hamiltonian whose ground state we want to find.
        ansatz (str): Optional, name of ansatz quantum circuit to use, default='EfficientSU2'
        ansatz_config (dict): Optional, configuration parameters for the ansatz circuit.
        x0 (array_like): Optional, initial vector of parameters.
        optimizer (str): Optional, string specifying classical optimizer, default='SPSA'.
        optimizer_config (dict): Optional, configuration parameters for the optimizer.
        shots (int): Optional, number of shots to take per circuit.
        use_measurement_mitigation (bool): Optional, use measurement mitigation, default=False.

    Returns:
        OptimizeResult: The result in SciPy optimization format.
    """

    # Split the Hamiltonian into two arrays, one for coefficients, the other for
    # operator strings
    coeffs = np.array([item[0] for item in hamiltonian], dtype=complex)
    op_strings = [item[1] for item in hamiltonian]
    # The number of qubits needed is given by the number of elements in the strings
    # the defiune the Hamiltonian. Here we grab this data from the first element.
    num_qubits = len(op_strings[0])

    # We grab the requested ansatz circuit class from the Qiskit circuit library
    # n_local module and configure it using the number of qubits and options
    # passed in the ansatz_config.
    ansatz_instance = getattr(lib_local, ansatz)
    ansatz_circuit = ansatz_instance(num_qubits, **ansatz_config)

    # Here we use our convenence function from Appendix B to get measurement circuits
    # with the correct single-qubit rotation gates.
    meas_circs = opstr_to_meas_circ(op_strings)

    # When computing the expectation value for the energy, we need to know if we
    # evaluate a Z measurement or and identity measurement.  Here we take and X and Y
    # operator in the strings and convert it to a Z since we added the rotations
    # with the meas_circs.
    meas_strings = [string.replace("X", "Z").replace("Y", "Z") for string in op_strings]

    # Take the ansatz circuits, add the single-qubit measurement basis rotations from
    # meas_circs, and finally append the measurements themselves.
    full_circs = [
        ansatz_circuit.compose(mcirc).measure_all(inplace=False) for mcirc in meas_circs
    ]

    # Get the number of parameters in the ansatz circuit.
    num_params = ansatz_circuit.num_parameters

    # Use a given initial state, if any, or do random initial state.
    if x0:
        x0 = np.asarray(x0, dtype=float)
        if x0.shape[0] != num_params:
            raise ValueError(
                "Number of params in x0 ({}) does not match number of ansatz parameters ({})".format(
                    x0.shape[0], num_params
                )
            )
    else:
        x0 = 2 * np.pi * np.random.rand(num_params)

    # Because we are in general targeting a real quantum system, our circuits must be transpiled
    # to match the system topology and, hopefully, optimize them.
    # Here we will set the transpiler to the most optimal settings where 'sabre' layout and
    # routing are used, along with full O3 optimization.

    # This works around a bug in Qiskit where Sabre routing fails for simulators (Issue #7098)
    trans_dict = {}
    if not backend.configuration().simulator:
        trans_dict = {"layout_method": "sabre", "routing_method": "sabre"}
    trans_circs = transpile(full_circs, backend, optimization_level=3, **trans_dict)

    # If using measurement mitigation we need to find out which physical qubits our transpiled
    # circuits actually measure, construct a mitigation object targeting our backend, and
    # finally calibrate our mitgation by running calibration circuits on the backend.
    if use_measurement_mitigation:
        maps = mthree.utils.final_measurement_mapping(trans_circs)
        mit = mthree.M3Mitigation(backend)
        mit.cals_from_system(maps)

    # Here we define a callback function that will stream the optimizer parameter vector
    # back to the user after each iteration.  This uses the `user_messenger` object.
    # Here we convert to a list so that the return is user readable locally, but
    # this is not required.
    def callback(xk):
        user_messenger.publish(list(xk))

    # This is the primary VQE function executed by the optimizer. This function takes the
    # parameter vector as input and returns the energy evaluated using an ansatz circuit
    # bound with those parameters.
    def vqe_func(params):
        # Attach (bind) parameters in params vector to the transpiled circuits.
        bound_circs = [circ.bind_parameters(params) for circ in trans_circs]

        # Submit the job and get the resultant counts back
        counts = backend.run(bound_circs, shots=shots).result().get_counts()

        # If using measurement mitigation apply the correction and
        # compute expectation values from the resultant quasiprobabilities
        # using the measurement strings.
        if use_measurement_mitigation:
            quasi_collection = mit.apply_correction(counts, maps)
            expvals = quasi_collection.expval(meas_strings)
        # If not doing any mitigation just compute expectation values
        # from the raw counts using the measurement strings.
        # Since Qiskit does not have such functionality we use the convenence
        # function from the mthree mitigation module.
        else:
            expvals = mthree.utils.expval(counts, meas_strings)

        # The energy is computed by simply taking the product of the coefficients
        # and the computed expectation values and summing them. Here we also
        # take just the real part as the coefficients can possibly be complex,
        # but the energy (eigenvalue) of a Hamiltonian is always real.
        energy = np.sum(coeffs * expvals).real
        return energy

    # Here is where we actually perform the computation.  We begin by seeing what
    # optimization routine the user has requested, eg. SPSA verses SciPy ones,
    # and dispatch to the correct optimizer.  The selected optimizer starts at
    # x0 and calls 'vqe_func' everytime the optimizer needs to evaluate the cost
    # function.  The result is returned as a SciPy OptimizerResult object.
    # Additionally, after every iteration, we use the 'callback' function to
    # publish the interim results back to the user. This is important to do
    # so that if the Program terminates unexpectedly, the user can start where they
    # left off.

    # Since SPSA is not in SciPy need if statement
    if optimizer == "SPSA":
        res = fmin_spsa(vqe_func, x0, args=(), **optimizer_config, callback=callback)
    # All other SciPy optimizers here
    else:
        res = opt.minimize(
            vqe_func, x0, method=optimizer, options=optimizer_config, callback=callback
        )
    # Return result. OptimizeResult is a subclass of dict.
    return res


def opstr_to_meas_circ(op_str):
    """Takes a list of operator strings and makes circuit with the correct post-rotations for measurements.

    Parameters:
        op_str (list): List of strings representing the operators needed for measurements.

    Returns:
        list: List of circuits for measurement post-rotations
    """
    num_qubits = len(op_str[0])
    circs = []
    for op in op_str:
        qc = QuantumCircuit(num_qubits)
        for idx, item in enumerate(op):
            if item == "X":
                qc.h(num_qubits - idx - 1)
            elif item == "Y":
                qc.sdg(num_qubits - idx - 1)
                qc.h(num_qubits - idx - 1)
        circs.append(qc)
    return circs


def fmin_spsa(
    func,
    x0,
    args=(),
    maxiter=100,
    a=1.0,
    alpha=0.602,
    c=1.0,
    gamma=0.101,
    callback=None,
):
    """
    Minimization of scalar function of one or more variables using simultaneous
    perturbation stochastic approximation (SPSA).

    Parameters:
        func (callable): The objective function to be minimized.

                          ``fun(x, *args) -> float``

                          where x is an 1-D array with shape (n,) and args is a
                          tuple of the fixed parameters needed to completely
                          specify the function.

        x0 (ndarray): Initial guess. Array of real elements of size (n,),
                      where ‘n’ is the number of independent variables.

        maxiter (int): Maximum number of iterations.  The number of function
                       evaluations is twice as many. Optional.

        a (float): SPSA gradient scaling parameter. Optional.

        alpha (float): SPSA gradient scaling exponent. Optional.

        c (float):  SPSA step size scaling parameter. Optional.

        gamma (float): SPSA step size scaling exponent. Optional.

        callback (callable): Function that accepts the current parameter vector
                             as input.

    Returns:
        OptimizeResult: Solution in SciPy Optimization format.

    Notes:
        See the `SPSA homepage <https://www.jhuapl.edu/SPSA/>`_ for usage and
        additional extentions to the basic version implimented here.
    """
    A = 0.01 * maxiter
    x0 = np.asarray(x0)
    x = x0

    for kk in range(maxiter):
        ak = a * (kk + 1.0 + A) ** -alpha
        ck = c * (kk + 1.0) ** -gamma
        # Bernoulli distribution for randoms
        deltak = 2 * np.random.randint(2, size=x.shape[0]) - 1
        grad = (func(x + ck * deltak, *args) - func(x - ck * deltak, *args)) / (
            2 * ck * deltak
        )
        x -= ak * grad

        if callback is not None:
            callback(x)

    return OptimizeResult(
        fun=func(x, *args),
        x=x,
        nit=maxiter,
        nfev=2 * maxiter,
        message="Optimization terminated successfully.",
        success=True,
    )
