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

"""Source code for the QKA Qiskit Runtime program."""

# pylint: disable=invalid-name

import itertools
import json
import numpy as np
from numpy.random import RandomState
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.compiler import transpile
from cvxopt import matrix, solvers  # pylint: disable=import-error


class FeatureMap:
    """Mapping data with the feature map."""

    def __init__(self, feature_dimension, entangler_map=None):
        """
        Args:
            feature_dimension (int): number of features, twice the number
                                     of qubits for this encoding
            entangler_map (list[list]): connectivity of qubits with a list of [source, target],
                                        or None for full entanglement. Note that the order in
                                        the list is the order of applying the two-qubit gate.
        Raises:
            ValueError: If the value of ``feature_dimension`` is not an even integer.
        """

        if isinstance(feature_dimension, int):
            if feature_dimension % 2 == 0:
                self._feature_dimension = feature_dimension
            else:
                raise ValueError("Feature dimension must be an even integer.")
        else:
            raise ValueError("Feature dimension must be an even integer.")

        self._num_qubits = int(feature_dimension / 2)

        if entangler_map is None:
            self._entangler_map = [
                [i, j]
                for i in range(self._feature_dimension)
                for j in range(i + 1, self._feature_dimension)
            ]
        else:
            self._entangler_map = entangler_map

        self._num_parameters = self._num_qubits

    def construct_circuit(
        self, x=None, parameters=None, q=None, inverse=False, name=None
    ):
        """Construct the feature map circuit.

        Args:
            x (numpy.ndarray): data vector of size feature_dimension
            parameters (numpy.ndarray): optional parameters in feature map
            q (QauntumRegister): the QuantumRegister object for the circuit
            inverse (bool): whether or not to invert the circuit
            name (str): name of circuit

        Returns:
            QuantumCircuit: a quantum circuit transforming data x
        Raises:
            ValueError: If the input parameters or vector are invalid
        """

        if parameters is not None:
            if isinstance(parameters, (int, float)):
                raise ValueError("Parameters must be a list.")
            if len(parameters) == 1:
                parameters = parameters * np.ones(self._num_qubits)
            else:
                if len(parameters) != self._num_parameters:
                    raise ValueError(
                        "The number of feature map parameters must be {}.".format(
                            self._num_parameters
                        )
                    )

        if len(x) != self._feature_dimension:
            raise ValueError(
                "The input vector must be of length {}.".format(self._feature_dimension)
            )

        if q is None:
            q = QuantumRegister(self._num_qubits, name="q")

        circuit = QuantumCircuit(q, name=name)

        for i in range(self._num_qubits):
            circuit.ry(-parameters[i], q[i])

        for source, target in self._entangler_map:
            circuit.cz(q[source], q[target])

        for i in range(self._num_qubits):
            circuit.rz(-2 * x[2 * i + 1], q[i])
            circuit.rx(-2 * x[2 * i], q[i])

        if inverse:
            return circuit.inverse()
        else:
            return circuit

    def to_json(self):
        """Return JSON representation of this object.

        Returns:
            str: JSON string representing this object.
        """
        return json.dumps(
            {
                "feature_dimension": self._feature_dimension,
                "entangler_map": self._entangler_map,
            }
        )

    @classmethod
    def from_json(cls, data):
        """Return an instance of this class from the JSON representation.

        Args:
            data (str): JSON string representing an object.

        Returns:
            cls: An instance of this class.
        """
        return cls(**json.loads(data))


class KernelMatrix:
    """Build the kernel matrix from a quantum feature map."""

    def __init__(self, feature_map, backend, initial_layout=None):
        """
        Args:
            feature_map: the feature map object
            backend (Backend): the backend instance
            initial_layout (list or dict): initial position of virtual
                                           qubits on the physical qubits
                                           of the quantum device
        """

        self._feature_map = feature_map
        self._feature_map_circuit = self._feature_map.construct_circuit
        self._backend = backend
        self._initial_layout = initial_layout

        self.results = {}

    def construct_kernel_matrix(self, x1_vec, x2_vec, parameters=None):
        """Create the kernel matrix for a given feature map and input data.

        With the qasm simulator or real backends, compute order 'n^2'
        states Phi^dag(y)Phi(x)|0> for input vectors x and y.

        Args:
            x1_vec (numpy.ndarray): NxD array of training data or test data,
                                    where N is the number of samples
                                    and D is the feature dimension
            x2_vec (numpy.ndarray): MxD array of training data or support
                                    vectors, where M is the number of samples
                                    and D is the feature dimension
            parameters (numpy.ndarray): optional parameters in feature map

        Returns:
           numpy.ndarray: the kernel matrix
        """

        is_identical = False
        if np.array_equal(x1_vec, x2_vec):
            is_identical = True

        experiments = []

        measurement_basis = "0" * self._feature_map._num_qubits

        if is_identical:

            my_product_list = list(
                itertools.combinations(range(len(x1_vec)), 2)
            )  # all pairwise combos of datapoint indices

            for index_1, index_2 in my_product_list:

                circuit_1 = self._feature_map_circuit(
                    x=x1_vec[index_1],
                    parameters=parameters,
                    name="{}_{}".format(index_1, index_2),
                )
                circuit_2 = self._feature_map_circuit(
                    x=x1_vec[index_2], parameters=parameters, inverse=True
                )
                circuit = circuit_1.compose(circuit_2)
                circuit.measure_all()
                experiments.append(circuit)

            experiments = transpile(
                experiments, backend=self._backend, initial_layout=self._initial_layout
            )
            program_data = self._backend.run(experiments, shots=8192).result()

            self.results["program_data"] = program_data

            mat = np.eye(
                len(x1_vec), len(x1_vec)
            )  # kernel matrix element on the diagonal is always 1
            for experiment, [index_1, index_2] in enumerate(my_product_list):

                counts = program_data.get_counts(experiment=experiment)
                shots = sum(counts.values())

                mat[index_1][index_2] = (
                    counts.get(measurement_basis, 0) / shots
                )  # kernel matrix element is the probability of measuring all 0s
                mat[index_2][index_1] = mat[index_1][
                    index_2
                ]  # kernel matrix is symmetric

            return mat

        else:

            for index_1, point_1 in enumerate(x1_vec):
                for index_2, point_2 in enumerate(x2_vec):

                    circuit_1 = self._feature_map_circuit(
                        x=point_1,
                        parameters=parameters,
                        name="{}_{}".format(index_1, index_2),
                    )
                    circuit_2 = self._feature_map_circuit(
                        x=point_2, parameters=parameters, inverse=True
                    )
                    circuit = circuit_1.compose(circuit_2)
                    circuit.measure_all()
                    experiments.append(circuit)

            experiments = transpile(
                experiments, backend=self._backend, initial_layout=self._initial_layout
            )
            program_data = self._backend.run(experiments, shots=8192).result()

            self.results["program_data"] = program_data

            mat = np.zeros((len(x1_vec), len(x2_vec)))
            i = 0
            for index_1, _ in enumerate(x1_vec):
                for index_2, _ in enumerate(x2_vec):

                    counts = program_data.get_counts(experiment=i)
                    shots = sum(counts.values())

                    mat[index_1][index_2] = counts.get(measurement_basis, 0) / shots
                    i += 1

            return mat


class QKA:
    """The quantum kernel alignment algorithm."""

    def __init__(self, feature_map, backend, initial_layout=None, user_messenger=None):
        """Constructor.

        Args:
            feature_map (partial obj): the quantum feature map object
            backend (Backend): the backend instance
            initial_layout (list or dict): initial position of virtual qubits on
                                           the physical qubits of the quantum device
            user_messenger (UserMessenger): used to publish interim results.
        """

        self.feature_map = feature_map
        self.feature_map_circuit = self.feature_map.construct_circuit
        self.backend = backend
        self.initial_layout = initial_layout
        self.num_parameters = self.feature_map._num_parameters

        self._user_messenger = user_messenger
        self.result = {}
        self.kernel_matrix = KernelMatrix(
            feature_map=self.feature_map,
            backend=self.backend,
            initial_layout=self.initial_layout,
        )

    def spsa_parameters(self):
        """Return array of precomputed SPSA parameters.

        The i-th optimization step, i>=0, the parameters evolve as

            a_i = a / (i + 1 + A) ** alpha,
            c_i = c / (i + 1) ** gamma,

        for fixed coefficents a, c, alpha, gamma, A.

        Returns:
            numpy.ndarray: spsa parameters
        """
        spsa_params = np.zeros((5))
        spsa_params[0] = 0.05  # a
        spsa_params[1] = 0.1  # c
        spsa_params[2] = 0.602  # alpha
        spsa_params[3] = 0.101  # gamma
        spsa_params[4] = 0  # A

        return spsa_params

    def cvxopt_solver(self, K, y, C, max_iters=10000, show_progress=False):
        """Convex optimization of SVM objective using cvxopt.

        Args:
            K (numpy.ndarray): nxn kernel (Gram) matrix
            y (numpy.ndarray): nx1 vector of labels +/-1
            C (float): soft-margin penalty
            max_iters (int): maximum iterations for the solver
            show_progress (bool): print progress of solver

        Returns:
            dict: results from the solver
        """

        if y.ndim == 1:
            y = y[:, np.newaxis]
        H = np.outer(y, y) * K
        f = -np.ones(y.shape)

        n = K.shape[1]  # number of training points

        y = y.astype("float")

        P = matrix(H)
        q = matrix(f)
        G = matrix(np.vstack((-np.eye((n)), np.eye((n)))))
        h = matrix(np.vstack((np.zeros((n, 1)), np.ones((n, 1)) * C)))
        A = matrix(y, y.T.shape)
        b = matrix(np.zeros(1), (1, 1))

        solvers.options["maxiters"] = max_iters
        solvers.options["show_progress"] = show_progress

        ret = solvers.qp(P, q, G, h, A, b, kktsolver="ldl")

        return ret

    def spsa_step_one(self, lambdas, spsa_params, count):
        """Evaluate +/- perturbations of kernel parameters (lambdas).

        Args:
            lambdas (numpy.ndarray): kernel parameters at step 'count' in SPSA optimization loop
            spsa_params (numpy.ndarray): SPSA parameters
            count (int): the current step in the SPSA optimization loop

        Returns:
            numpy.ndarray: kernel parameters in + direction
            numpy.ndarray: kernel parameters in - direction
            numpy.ndarray: random vector with elements {-1,1}
        """

        prng = RandomState(count)

        c_spsa = float(spsa_params[1]) / np.power(count + 1, spsa_params[3])
        delta = 2 * prng.randint(0, 2, size=np.shape(lambdas)[0]) - 1

        lambda_plus = lambdas + c_spsa * delta
        lambda_minus = lambdas - c_spsa * delta

        return lambda_plus, lambda_minus, delta

    def spsa_step_two(self, cost_plus, cost_minus, lambdas, spsa_params, delta, count):
        """Evaluate one iteration of SPSA on SVM objective function F and
        return updated kernel parameters.

        F(alpha, lambda) = 1^T * alpha - (1/2) * alpha^T * Y * K * Y * alpha

        Args:
            cost_plus (float): objective function F(alpha_+, lambda_+)
            cost_minus (float): objective function F(alpha_-, lambda_-)
            lambdas (numpy.ndarray): kernel parameters at step 'count' in SPSA optimization loop
            spsa_params (numpy.ndarray): SPSA parameters
            delta (numpy.ndarray): random vector with elements {-1,1}
            count(int): the current step in the SPSA optimization loop

        Returns:
            float: estimate of updated SVM objective function F using average
                   of F(alpha_+, lambda_+) and F(alpha_-, lambda_-)
            numpy.ndarray: updated values of the kernel parameters
                           after one SPSA optimization step
        """

        a_spsa = float(spsa_params[0]) / np.power(
            count + 1 + spsa_params[4], spsa_params[2]
        )
        c_spsa = float(spsa_params[1]) / np.power(count + 1, spsa_params[3])

        g_spsa = (cost_plus - cost_minus) * delta / (2.0 * c_spsa)

        lambdas_new = lambdas - a_spsa * g_spsa
        lambdas_new = lambdas_new.flatten()

        cost_final = (cost_plus + cost_minus) / 2

        return cost_final, lambdas_new

    def align_kernel(
        self, data, labels, initial_kernel_parameters=None, maxiters=1, C=1
    ):
        """Align the quantum kernel.

        Uses SPSA for minimization over kernel parameters (lambdas) and
        convex optimization for maximization over lagrange multipliers (alpha):

        min_lambda max_alpha 1^T * alpha - (1/2) * alpha^T * Y * K_lambda * Y * alpha

        Args:
            data (numpy.ndarray): NxD array of training data, where N is the
                                  number of samples and D is the feature dimension
            labels (numpy.ndarray): Nx1 array of +/-1 labels of the N training samples
            initial_kernel_parameters (numpy.ndarray): Initial parameters of the quantum kernel
            maxiters (int): number of SPSA optimization steps
            C (float): penalty parameter for the soft-margin support vector machine

        Returns:
            dict: the results of kernel alignment
        """

        if initial_kernel_parameters is not None:
            lambdas = initial_kernel_parameters
        else:
            lambdas = np.random.uniform(-1.0, 1.0, size=(self.num_parameters))

        spsa_params = self.spsa_parameters()

        lambda_save = []
        cost_final_save = []

        for count in range(maxiters):

            lambda_plus, lambda_minus, delta = self.spsa_step_one(
                lambdas=lambdas, spsa_params=spsa_params, count=count
            )

            kernel_plus = self.kernel_matrix.construct_kernel_matrix(
                x1_vec=data, x2_vec=data, parameters=lambda_plus
            )
            kernel_minus = self.kernel_matrix.construct_kernel_matrix(
                x1_vec=data, x2_vec=data, parameters=lambda_minus
            )

            ret_plus = self.cvxopt_solver(K=kernel_plus, y=labels, C=C)
            cost_plus = -1 * ret_plus["primal objective"]

            ret_minus = self.cvxopt_solver(K=kernel_minus, y=labels, C=C)
            cost_minus = -1 * ret_minus["primal objective"]

            cost_final, lambda_best = self.spsa_step_two(
                cost_plus=cost_plus,
                cost_minus=cost_minus,
                lambdas=lambdas,
                spsa_params=spsa_params,
                delta=delta,
                count=count,
            )

            lambdas = lambda_best

            interim_result = {"cost": cost_final, "kernel_parameters": lambdas}

            self._user_messenger.publish(interim_result)

            lambda_save.append(lambdas)
            cost_final_save.append(cost_final)

        # Evaluate aligned kernel matrix with optimized set of
        # parameters averaged over last 10% of SPSA steps:
        num_last_lambdas = int(len(lambda_save) * 0.10)
        if num_last_lambdas > 0:
            last_lambdas = np.array(lambda_save)[-num_last_lambdas:, :]
            lambdas = np.sum(last_lambdas, axis=0) / num_last_lambdas
        else:
            lambdas = np.array(lambda_save)[-1, :]

        kernel_best = self.kernel_matrix.construct_kernel_matrix(
            x1_vec=data, x2_vec=data, parameters=lambdas
        )

        self.result["aligned_kernel_parameters"] = lambdas
        self.result["aligned_kernel_matrix"] = kernel_best

        return self.result


def main(backend, user_messenger, **kwargs):
    """Entry function."""

    # Reconstruct the feature map object.
    feature_map = kwargs.get("feature_map")
    fm = FeatureMap.from_json(feature_map)

    data = kwargs.get("data")
    labels = kwargs.get("labels")
    initial_kernel_parameters = kwargs.get("initial_kernel_parameters", None)
    maxiters = kwargs.get("maxiters", 1)
    C = kwargs.get("C", 1)
    initial_layout = kwargs.get("initial_layout", None)

    qka = QKA(
        feature_map=fm,
        backend=backend,
        initial_layout=initial_layout,
        user_messenger=user_messenger,
    )
    qka_results = qka.align_kernel(
        data=data,
        labels=labels,
        initial_kernel_parameters=initial_kernel_parameters,
        maxiters=maxiters,
        C=C,
    )

    return qka_results
