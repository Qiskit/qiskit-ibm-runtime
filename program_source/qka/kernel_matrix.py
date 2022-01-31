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

"""The KernelMatrix class."""

import itertools

import numpy as np

from qiskit.compiler import transpile


class KernelMatrix:
    """Build the kernel matrix from a quantum feature map."""

    def __init__(self, feature_map, backend, initial_layout=None):
        """
        Args:
            feature_map (int): the feature map object
            backend (Backend): the backend instance
            initial layout (list or dict): initial position of virtual qubits on the physical
                qubits of the quantum device
        """

        self._feature_map = feature_map
        self._feature_map_circuit = (
            self._feature_map.construct_circuit
        )  # the feature map circuit
        self._backend = backend
        self._initial_layout = initial_layout

        self.results = {}  # store the results object (program_data)

    def construct_kernel_matrix(self, x1_vec, x2_vec, parameters=None):
        """Create the kernel matrix for a given feature map and input data.

        With the qasm simulator or real backends, compute order 'n^2'
        states Phi^dag(y)Phi(x)|0> for input vectors x and y.

        Args:
            x1_vec (numpy.ndarray): NxD array of training data or test data, where N is the
                number of samples and D is the feature dimension
            x2_vec (numpy.ndarray): MxD array of training data or support vectors, where M
                is the number of samples and D is the feature dimension
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

            program_data = self._run_circuits(experiments)
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

            program_data = self._run_circuits(experiments)
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

    def _run_circuits(self, circuits):
        """Execute the input circuits."""

        transpiled = transpile(
            circuits, backend=self._backend, initial_layout=self._initial_layout
        )
        return self._backend.run(transpiled, shots=8192).result()
