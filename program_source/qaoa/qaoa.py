# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""A self-contained QAOA runtime with the SWAP strategies."""

from typing import Dict, List, Optional, Set, Tuple
from warnings import warn

import copy
import retworkx as rx
import numpy as np

from qiskit import QuantumCircuit
from qiskit.algorithms import VQE
from qiskit.algorithms.optimizers import SPSA
from qiskit.circuit import ParameterVector, Parameter, Gate
from qiskit.circuit.library import NLocal, EvolvedOperatorAnsatz
from qiskit.circuit.exceptions import CircuitError
from qiskit.circuit.quantumregister import QuantumRegister
from qiskit.converters import circuit_to_dag
from qiskit.opflow import PauliExpectation, CVaRExpectation, OperatorBase
from qiskit.opflow.primitive_ops.pauli_sum_op import PauliSumOp
from qiskit.utils import QuantumInstance
from qiskit.providers.backend import Backend
from qiskit.dagcircuit import DAGCircuit
from qiskit.ignis.mitigation import TensoredMeasFitter
from qiskit.exceptions import QiskitError
from qiskit.circuit.library.standard_gates.equivalence_library import (
    StandardEquivalenceLibrary as std_eqlib,
)
from qiskit.transpiler import (
    PassManager,
    CouplingMap,
    AnalysisPass,
    TransformationPass,
    Layout,
)
from qiskit.transpiler.passes import (
    Collect2qBlocks,
    ConsolidateBlocks,
    Optimize1qGatesDecomposition,
    FullAncillaAllocation,
    EnlargeWithAncilla,
    ApplyLayout,
    BasisTranslator,
    UnrollCustomDefinitions,
)
from qiskit.transpiler.passes.calibration.builders import RZXCalibrationBuilderNoEcho
from qiskit.transpiler.passes.optimization.echo_rzx_weyl_decomposition import (
    EchoRZXWeylDecomposition,
)

from qiskit_optimization import QuadraticProgram


class Publisher:
    """Class used to publish interim results."""

    def __init__(self, messenger):
        self._messenger = messenger

    def callback(self, *args, **kwargs):
        text = list(args)
        for k, v in kwargs.items():
            text.append({k: v})
        self._messenger.publish(text)


# begin QAOA Gate


class QAOAAnsatz(EvolvedOperatorAnsatz):
    """A generalized QAOA quantum circuit with a support of custom initial states and mixers.

    References:

        [1]: Farhi et al., A Quantum Approximate Optimization Algorithm.
            `arXiv:1411.4028 <https://arxiv.org/pdf/1411.4028>`_
    """

    def __init__(
        self,
        cost_operator=None,
        reps: int = 1,
        initial_state: Optional[QuantumCircuit] = None,
        mixer_operator=None,
        name: str = "QAOA",
    ):
        r"""
        Args:
            cost_operator (OperatorBase, optional): The operator representing the cost of
                the optimization problem, denoted as :math:`U(C, \gamma)` in the original paper.
                Must be set either in the constructor or via property setter.
            reps (int): The integer parameter p, which determines the depth of the circuit,
                as specified in the original paper, default is 1.
            initial_state (QuantumCircuit, optional): An optional initial state to use.
                If `None` is passed then a set of Hadamard gates is applied as an initial state
                to all qubits.
            mixer_operator (OperatorBase or QuantumCircuit, optional): An optional custom mixer
                to use instead of the global X-rotations, denoted as :math:`U(B, \beta)`
                in the original paper. Can be an operator or an optionally parameterized quantum
                circuit.
            name (str): A name of the circuit, default 'qaoa'
        """
        super().__init__(reps=reps, name=name)

        self._cost_operator = None
        self._reps = reps
        self._initial_state = initial_state
        self._mixer = mixer_operator

        # set this circuit as a not-built circuit
        self._bounds = None

        # store cost operator and set the registers if the operator is not None
        self.cost_operator = cost_operator

    def _check_configuration(self, raise_on_failure: bool = True) -> bool:
        valid = True

        if not super()._check_configuration(raise_on_failure):
            return False

        if self.cost_operator is None:
            valid = False
            if raise_on_failure:
                raise ValueError(
                    "The operator representing the cost of the optimization problem is not set"
                )

        if (
            self.initial_state is not None
            and self.initial_state.num_qubits != self.num_qubits
        ):
            valid = False
            if raise_on_failure:
                raise ValueError(
                    "The number of qubits of the initial state {} does not match "
                    "the number of qubits of the cost operator {}".format(
                        self.initial_state.num_qubits, self.num_qubits
                    )
                )

        if (
            self.mixer_operator is not None
            and self.mixer_operator.num_qubits != self.num_qubits
        ):
            valid = False
            if raise_on_failure:
                raise ValueError(
                    "The number of qubits of the mixer {} does not match "
                    "the number of qubits of the cost operator {}".format(
                        self.mixer_operator.num_qubits, self.num_qubits
                    )
                )

        return valid

    @property
    def parameter_bounds(
        self,
    ) -> Optional[List[Tuple[Optional[float], Optional[float]]]]:
        """The parameter bounds for the unbound parameters in the circuit.

        Returns:
            A list of pairs indicating the bounds, as (lower, upper). None indicates an unbounded
            parameter in the corresponding direction. If None is returned, problem is fully
            unbounded.
        """
        if self._bounds is not None:
            return self._bounds

        # if the mixer is a circuit, we set no bounds
        if isinstance(self.mixer_operator, QuantumCircuit):
            return None

        # default bounds: None for gamma (cost operator), [0, 2pi] for gamma (mixer operator)
        beta_bounds = (0, 2 * np.pi)
        gamma_bounds = (None, None)
        bounds = []

        if not _is_pauli_identity(self.mixer_operator):
            bounds += self.reps * [beta_bounds]

        if not _is_pauli_identity(self.cost_operator):
            bounds += self.reps * [gamma_bounds]

        return bounds

    @parameter_bounds.setter
    def parameter_bounds(
        self, bounds: Optional[List[Tuple[Optional[float], Optional[float]]]]
    ) -> None:
        """Set the parameter bounds.

        Args:
            bounds: The new parameter bounds.
        """
        self._bounds = bounds

    @property
    def operators(self):
        """The operators that are evolved in this circuit.

        Returns:
             List[Union[OperatorBase, QuantumCircuit]]: The operators to be evolved (and circuits)
                in this ansatz.
        """
        return [self.cost_operator, self.mixer_operator]

    @property
    def cost_operator(self):
        """Returns an operator representing the cost of the optimization problem.

        Returns:
            OperatorBase: cost operator.
        """
        return self._cost_operator

    @cost_operator.setter
    def cost_operator(self, cost_operator) -> None:
        """Sets cost operator.

        Args:
            cost_operator (OperatorBase, optional): cost operator to set.
        """
        self._cost_operator = cost_operator
        self.qregs = [QuantumRegister(self.num_qubits, name="q")]
        self._invalidate()

    @property
    def reps(self) -> int:
        """Returns the `reps` parameter, which determines the depth of the circuit."""
        return self._reps

    @reps.setter
    def reps(self, reps: int) -> None:
        """Sets the `reps` parameter."""
        self._reps = reps
        self._invalidate()

    @property
    def initial_state(self) -> Optional[QuantumCircuit]:
        """Returns an optional initial state as a circuit"""
        if self._initial_state is not None:
            return self._initial_state

        # if no initial state is passed and we know the number of qubits, then initialize it.
        if self.cost_operator is not None:
            return _get_default_initial_state(self.cost_operator)

        # otherwise we cannot provide a default
        return None

    @initial_state.setter
    def initial_state(self, initial_state: Optional[QuantumCircuit]) -> None:
        """Sets initial state."""
        self._initial_state = initial_state
        self._invalidate()

    # we can't directly specify OperatorBase as a return type, it causes a circular import
    # and pylint objects if return type is not documented
    @property
    def mixer_operator(self):
        """Returns an optional mixer operator expressed as an operator or a quantum circuit.

        Returns:
            OperatorBase or QuantumCircuit, optional: mixer operator or circuit.
        """
        if self._mixer is not None:
            return self._mixer

        # if no mixer is passed and we know the number of qubits, then initialize it.
        if self.cost_operator is not None:
            return _get_default_mixer(self.cost_operator)

        # otherwise we cannot provide a default
        return None

    @mixer_operator.setter
    def mixer_operator(self, mixer_operator) -> None:
        """Sets mixer operator.

        Args:
            mixer_operator (OperatorBase or QuantumCircuit, optional): mixer operator or circuit
                to set.
        """
        self._mixer = mixer_operator
        self._invalidate()

    def _build_gate(self):
        """Return a QAOAGate based on the current settings."""
        return QAOAGate(
            cost_operator=self.cost_operator,
            reps=self.reps,
            initial_state=self.initial_state,
            mixer_operator=self.mixer_operator,
            label=self.name,
        )

    def _build(self):
        if self._data is not None:
            return

        # need to check configuration here to ensure the operators are not None
        self._check_configuration()
        self._data = []
        num_qubits = self.num_qubits

        qr = QuantumRegister(num_qubits, "q")
        if qr.name not in [qreg.name for qreg in self.qregs]:
            # if the register already exists, probably because of a previous composition.
            # Otherwise, add it.
            self.add_register(qr)

        self._append(
            self._build_gate(),
            qargs=self.qubits,
            cargs=[],
        )

        num_cost = 0 if _is_pauli_identity(self.cost_operator) else 1
        if isinstance(self.mixer_operator, QuantumCircuit):
            num_mixer = self.mixer_operator.num_parameters
        else:
            num_mixer = 0 if _is_pauli_identity(self.mixer_operator) else 1

        betas = ParameterVector("β", self.reps * num_mixer)
        gammas = ParameterVector("γ", self.reps * num_cost)

        # Create a permutation to take us from (cost_1, mixer_1, cost_2, mixer_2, ...)
        # to (cost_1, cost_2, ..., mixer_1, mixer_2, ...), or if the mixer is a circuit
        # with more than 1 parameters, from (cost_1, mixer_1a, mixer_1b, cost_2, ...)
        # to (cost_1, cost_2, ..., mixer_1a, mixer_1b, mixer_2a, mixer_2b, ...)
        reordered = []
        for rep in range(self.reps):
            reordered.extend(gammas[rep * num_cost : (rep + 1) * num_cost])
            reordered.extend(betas[rep * num_mixer : (rep + 1) * num_mixer])

        self.assign_parameters(reordered, inplace=True)


class QAOAGate(Gate):
    """A generalized QAOA gate with a support of custom initial states and mixers.

    References:

        [1]: Farhi et al., A Quantum Approximate Optimization Algorithm.
            `arXiv:1411.4028 <https://arxiv.org/pdf/1411.4028>`_
    """

    def __init__(
        self,
        cost_operator,
        reps: int = 1,
        initial_state: Optional[QuantumCircuit] = None,
        mixer_operator=None,
        label: str = None,
    ):
        r"""
        Args:
            cost_operator (OperatorBase, optional): The operator representing the cost of
                the optimization problem, denoted as :math:`U(C, \gamma)` in the original paper.
                Must be set either in the constructor or via property setter.
            reps (int): The integer parameter p, which determines the depth of the circuit,
                as specified in the original paper, default is 1.
            initial_state (QuantumCircuit, optional): An optional initial state to use.
                If `None` is passed then a set of Hadamard gates is applied as an initial state
                to all qubits.
            mixer_operator (OperatorBase or QuantumCircuit, optional): An optional custom mixer
                to use instead of the global X-rotations, denoted as :math:`U(B, \beta)`
                in the original paper. Can be an operator or an optionally parameterized quantum
                circuit.
            label (str): A label.
        Raises:
            AttributeError: when cost_operator and initial_state are not compatible
        """
        # pylint: disable=cyclic-import
        from qiskit.opflow import PauliOp, PauliTrotterEvolution

        self.cost_operator = cost_operator

        if initial_state is None:
            initial_state = _get_default_initial_state(cost_operator)
        else:
            if initial_state.num_qubits != cost_operator.num_qubits:
                raise AttributeError(
                    "initial_state and cost_operator has incompatible number of qubits"
                )

        if mixer_operator is None:
            mixer_operator = _get_default_mixer(cost_operator)

        self.mixer_operator = mixer_operator
        self.operators = [cost_operator, mixer_operator]
        self.reps = reps
        self.evolution = PauliTrotterEvolution()
        self.initial_state = initial_state

        # determine how many parameters the circuit will contain
        num_parameters = 0
        for op in self.operators:
            if isinstance(op, QuantumCircuit):
                num_parameters += op.num_parameters
            else:
                # check if the operator is just the identity, if yes, skip it
                if isinstance(op, PauliOp):
                    sig_qubits = np.logical_or(op.primitive.x, op.primitive.z)
                    if sum(sig_qubits) == 0:
                        continue
                num_parameters += 1

        super().__init__(
            "QAOA",
            self.operators[0].num_qubits,
            params=list(ParameterVector("t", reps * num_parameters)),
            label=label,
        )

    def _define(self):
        """Build the circuit by evolving the operators and using NLocal for the repetitions."""
        coeff = Parameter("c")
        circuits = []
        bind_parameter = []
        for op in self.operators:
            # if the operator is already the evolved circuit just append it
            if isinstance(op, QuantumCircuit):
                circuits.append(op)
                bind_parameter.append(False)
            else:
                evolved_op = self.evolution.convert((coeff * op).exp_i()).reduce()
                circuit = evolved_op.to_circuit()
                # if the operator was the identity it is amounts only to a global phase and no
                # parameter is added
                bind_parameter.append(circuit.num_parameters > 0)
                circuits.append(circuit)

        self.definition = (
            NLocal(
                circuits[0].num_qubits,
                rotation_blocks=[],
                entanglement_blocks=circuits,
                reps=self.reps,
                initial_state=self.initial_state,
            )
            .decompose()
            .assign_parameters(self.params)
        )


def _validate_operators(operators):
    if not isinstance(operators, list):
        operators = [operators]

    if len(operators) > 1:
        num_qubits = operators[0].num_qubits
        if any(operators[i].num_qubits != num_qubits for i in range(1, len(operators))):
            raise ValueError("All operators must act on the same number of qubits.")

    return operators


def _validate_prefix(parameter_prefix, operators):
    if isinstance(parameter_prefix, str):
        return len(operators) * [parameter_prefix]
    if len(parameter_prefix) != len(operators):
        raise ValueError("The number of parameter prefixes must match the operators.")

    return parameter_prefix


def _is_pauli_identity(operator):
    from qiskit.opflow import PauliOp

    if isinstance(operator, PauliOp):
        return not np.any(np.logical_or(operator.primitive.x, operator.primitive.z))
    return False


def _get_default_mixer(cost_operator):
    # local imports to avoid circular imports
    from qiskit.opflow import I, X

    num_qubits = cost_operator.num_qubits

    # Mixer is just a sum of single qubit X's on each qubit. Evolving by this operator
    # will simply produce rx's on each qubit.
    active_indices = _active_qubits(cost_operator)

    if len(active_indices) == 0:
        return 0 * (I ^ num_qubits)

    mixer_terms = [
        (I ^ left) ^ X ^ (I ^ (num_qubits - left - 1)) for left in active_indices
    ]
    return sum(mixer_terms)


def _get_default_initial_state(cost_operator):
    initial_state = QuantumCircuit(cost_operator.num_qubits)
    active_indices = _active_qubits(cost_operator)

    if len(active_indices) > 0:
        # Opflow indices are reversed with respect to circuit indices
        active_indices = [
            cost_operator.num_qubits - 1 - index for index in active_indices
        ]
        initial_state.h(active_indices)

    return initial_state


def _active_qubits(operator):
    from qiskit.opflow import PauliSumOp, PauliOp

    # active qubit selection only supported for PauliSumOps
    if isinstance(operator, PauliSumOp):
        sparse_pauli = operator.primitive
        paulis = sparse_pauli.paulis.to_labels()
    elif isinstance(operator, PauliOp):
        paulis = [operator.primitive.to_label()]
    else:
        return list(range(operator.num_qubits))

    # for each Pauli string get a list which Pauli is the identity (i.e. not active)
    is_identity = [
        list(map(lambda pauli: pauli == "I", pauli_string)) for pauli_string in paulis
    ]

    # use numpy act a logical and on each index across the Pauli strings
    idle_qubits = np.all(np.array(is_identity), axis=0)

    # return the indices of the qubits that are not idle
    active_indices = [index for index, idle in enumerate(idle_qubits) if not idle]

    return active_indices


# end QAOA gate


def line_coloring(num_vertices) -> Dict:
    """
    Creates an edge coloring of the line graph, corresponding to the optimal
    line swap strategy, given as a dictionary where the keys
    correspond to the different colors and the values are lists of edges (where edges
    are specified as tuples). The graph coloring consists of one color for all even-numbered
    edges and one color for all odd-numbered edges.
    Args:
        num_vertices: The number of vertices in the line graph
    Returns:
        Graph coloring as a dictionary of edge lists
    """
    line_coloring = {}
    for i in range(num_vertices - 1):
        line_coloring[(i, i + 1)] = i % 2
        line_coloring[(i + 1, i)] = i % 2
    return line_coloring


class SwapStrategy:
    """A class representing SWAP strategies for coupling maps.

    A swap strategy is a list of swap layers to apply to the physical coupling map. Each swap layer
    is specified by a set of tuples which correspond to the edges of the physical coupling map that
    are swapped. At each swap layer SWAP gates are applied to the corresponding edges. This class
    stores the permutations of the qubits resulting from the swap strategy.

    """

    def __init__(
        self,
        coupling_map: CouplingMap,
        swap_layers: List[List[Tuple[int, int]]],
        edge_coloring: Optional[Dict[Tuple[int, int], int]] = None,
    ):
        """
        Args:
            coupling_map: The coupling map the strategy is implemented for.
            swap_layers: The swap layers of the strategy, specified as a list of sets of
                edges (edges can be represented as lists, sets or tuples containing two integers).
            edge_coloring: (Optional) edge coloring of the coupling map, specified as a set of
                sets of edges (edges can be represented as lists, sets or tuples containing two
                integers). The edge coloring is used for efficient gate parallelization when
                using the swap strategy in a transpiler pass.
        """
        self.coupling_map = copy.deepcopy(coupling_map)
        self.num_vertices = coupling_map.size()
        self.swap_layers = swap_layers
        self.edge_coloring = edge_coloring
        self._distance_matrix = None
        self._inverse_composed_permutation = {0: list(range(self.num_vertices))}

    @property
    def coupling_map(self) -> CouplingMap:
        """Returns the coupling map of the SWAP strategy."""
        return self._coupling_map

    @coupling_map.setter
    def coupling_map(self, coupling_map: CouplingMap) -> None:
        """Sets the coupling map of the SWAP strategy."""
        self._coupling_map = coupling_map
        self._invalidate()

    @property
    def swap_layers(self) -> List:
        """Returns the SWAP layers of the SWAP strategy."""
        return self._swap_layers

    @swap_layers.setter
    def swap_layers(self, swap_layers: List) -> None:
        """Sets the SWAP layers of the SWAP strategy."""
        self._swap_layers = swap_layers
        self._invalidate()

    @property
    def max_distance(self, qubits: Optional[List] = None) -> Optional[int]:
        """
        Return the maximum distance in the SWAP strategy between a list of specified qubits or
        all qubits if no list is given.

        Args:
            qubits: List of qubits to consider.

        Returns:
            The maximum distance between qubits. None if two qubits in the list have no defined
            distance.
        """
        if qubits is None:
            qubits = list(range(self.num_vertices))

        max_distance = 0

        for i in range(len(qubits)):
            for j in range(i):
                qubit1 = qubits[i]
                qubit2 = qubits[j]
                if self.distance_matrix[qubit1][qubit2] is None:
                    return None

                max_distance = max(max_distance, self.distance_matrix[qubit1][qubit2])

        return max_distance

    def __len__(self) -> int:
        """Return the length of the strategy as the number of layers."""
        return len(self.swap_layers)

    def __repr__(self) -> str:
        """Print the swap strategy."""
        description = f"{self.__class__.__name__} with swap layers:\n"

        for layer in self.swap_layers:
            description += f"{layer},\n"

        description += f"on {self.coupling_map} coupling map."

        return description

    @property
    def distance_matrix(self) -> List[List]:
        """
        Returns the distance matrix of the SWAP strategy as a nested list, where the entry (i,j)
        corresponds to the number of SWAP layers that need to be applied to obtain a connection
        between physical qubits i and j.

        Returns:
            Distance matrix for the SWAP strategy as a nested list.
        """
        self._check_configuration(raise_on_failure=True)

        # Only compute the distance matrix if it has not been computed before
        if self._distance_matrix is None:
            distance_matrix = [
                [None] * self.num_vertices for _ in range(self.num_vertices)
            ]

            for i in range(self.num_vertices):
                distance_matrix[i][i] = 0

            for i in range(0, len(self.swap_layers) + 1):
                for [j, k] in self.swapped_coupling_map(i).get_edges():
                    if distance_matrix[j][k] is None:
                        distance_matrix[j][k] = i
                        distance_matrix[k][j] = i

            self._distance_matrix = distance_matrix

        return self._distance_matrix

    def permute_labels(self, permutation: List[int], inplace: bool = True):
        """
        Permute the labels of the underlying coupling map of the SWAP strategy
        and adapt the corresponding SWAP layers accordingly.

        Args:
            permutation: The permutation to swap labels by, specified as a list of integers
            inplace: Specifies whether the swap strategy object should be modified or a new
                swap strategy object created.

        Returns:
            A newly created swap strategy if inplace = False, else None
        """
        permuted_coupling_map = CouplingMap(
            couplinglist=[
                [permutation[edge[0]], permutation[edge[1]]]
                for edge in self.coupling_map.get_edges()
            ]
        )
        permuted_swap_layers = []
        for swap_layer in self.swap_layers:
            permuted_swap_layer = [
                (permutation[i], permutation[j]) for (i, j) in swap_layer
            ]
            permuted_swap_layers.append(permuted_swap_layer)

        if inplace:
            self.coupling_map = permuted_coupling_map
            self.swap_layers = permuted_swap_layers
        else:
            return SwapStrategy(
                coupling_map=permuted_coupling_map,
                swap_layers=permuted_swap_layers,
                edge_coloring=self.edge_coloring,
            )

    def new_connections(self, idx: int) -> List[Set]:
        """
        Returns the new connections obtained after applying the SWAP layer specified by idx, i.e.
        a list of qubit pairs that are adjacent to one another after idx steps of the SWAP strategy.

        Args:
            idx: The index of the SWAP layer. 1 refers to the first SWAP layer
                whereas idx = 0 will return the connections present in the original coupling map

        Returns:
            A set of edges representing the new qubit connections
        """
        connections = []
        for i in range(self.num_vertices):
            for j in range(i):
                if self.distance_matrix[i][j] == idx:
                    connections.append({i, j})

        return connections

    def missing_couplings(self) -> Set[Tuple[int, int]]:
        """Returns the set of couplings that cannot be reached."""
        physical_qubits = list(set(sum(self._coupling_map.get_edges(), ())))
        missed_edges = set()
        for i in range(len(physical_qubits)):
            for j in range(i + 1, len(physical_qubits)):
                missed_edges.add((physical_qubits[i], physical_qubits[j]))
                missed_edges.add((physical_qubits[j], physical_qubits[i]))

        for layer_idx in range(len(self) + 1):
            for edge in self.new_connections(layer_idx):
                for edge_tuple in [tuple(edge), tuple(edge)[::-1]]:
                    try:
                        missed_edges.remove(edge_tuple)
                    except KeyError:
                        pass

        return missed_edges

    def reaches_full_connectivity(self) -> bool:
        """Return True if the swap strategy reaches full connectivity."""
        return len(self.missing_couplings()) == 0

    def swapped_coupling_map(self, idx: int) -> CouplingMap:
        """
        Returns the coupling map after applying a specified number of SWAP layers
        from the SWAP strategy.

        Args:
            idx: The number of SWAP layers to apply. For idx = 0, the original coupling
                map is returned.

        Returns:
            The swapped coupling map.
        """
        permutation = self.inverse_composed_permutation(idx)

        edges = [
            [permutation[i], permutation[j]] for [i, j] in self.coupling_map.get_edges()
        ]

        return CouplingMap(couplinglist=edges)

    def apply_swap_layer(self, list_to_swap: List, idx: int) -> List:
        """
        Apply SWAPS from a layer specified by idx to a list of elements by
        interchanging their positions.

        Args:
            list_to_swap: The list of elements to swap
            idx: The index of the SWAP layer to apply

        Returns:
            The list with swapped elements
        """
        x = copy.copy(list_to_swap)

        for edge in self.swap_layers[idx]:
            (i, j) = tuple(edge)
            x[i], x[j] = x[j], x[i]

        return x

    def composed_permutation(self, idx) -> List[int]:
        """
        Returns the composed permutation of all SWAP layers applied up to a specified index.
        Permutations are represented by list of integers where the ith element corresponds
        to the mapping of i under the permutation.

        Args:
            idx: The number of SWAP layers to apply

        Returns:
            The permutation as a list of integer values
        """
        return self.invert_permutation(self.inverse_composed_permutation(idx))

    def inverse_composed_permutation(self, idx) -> List[int]:
        """
        Returns the inversed composed permutation of all SWAP layers applied up to a specified
        index. Permutations are represented by list of integers where the ith element corresponds
        to the mapping of i under the permutation.

        Args:
            idx: The number of SWAP layers to apply

        Returns:
            The inversed permutation as a list of integer values
        """
        # Only compute the inverse permutation if it has not been computed before
        self._check_configuration(raise_on_failure=True)
        try:
            return self._inverse_composed_permutation[idx]

        except KeyError:
            if idx == 0:
                return list(range(self.num_vertices))

            self._inverse_composed_permutation[idx] = self.apply_swap_layer(
                self.inverse_composed_permutation(idx - 1), idx - 1
            )

            return self._inverse_composed_permutation[idx]

    @staticmethod
    def invert_permutation(permutation: List) -> List:
        """
        Inverts a permutation specified by a list of integers where the ith element corresponds
        to the mapping of i under the permutation.

        Args:
            The original permutation

        Returns:
            The inverse of the permutation
        """
        inverse_permutation = [0] * len(permutation)
        for i, j in enumerate(permutation):
            if not isinstance(j, int):
                raise ValueError(f"Permutation contains non-integer element {j}.")
            if j > len(permutation):
                raise ValueError(
                    f"Permutation of length {len(permutation)} contains "
                    f"element {j} and is therefore invalid."
                )
            inverse_permutation[j] = i
        return inverse_permutation

    def _invalidate(self) -> None:
        """Reset all precomputed properties of the SWAP strategy"""
        self._distance_matrix = None
        self._inverse_composed_permutation = {}

    def _check_configuration(self, raise_on_failure: bool = True) -> bool:
        """
        Check that the configuration of the SWAP strategy is valid

        Args:
            raise_on_failure: Specifies whether the function should raise an exception
                if the SWAP strategy is invalid.

        Returns:
            True if the SWAP strategy is valid, False otherwise (unless an exception is raised)
        """
        if self.coupling_map is None:
            if raise_on_failure:
                raise RuntimeError("The coupling map is None.")
            return False

        if self.swap_layers is None:
            if raise_on_failure:
                raise RuntimeError("SWAP layers are None.")
            return False

        edge_set = set(self.coupling_map.get_edges())
        for i, layer in enumerate(self.swap_layers):
            for edge in layer:
                if edge not in edge_set:
                    if raise_on_failure:
                        raise RuntimeError(
                            f"The {i}th SWAP layer contains the edge {edge} which is not "
                            f"part of the underlying coupling map with {edge_set} edges."
                        )
                    return False

        return True

    def embed_in(self, coupling_map, vertex_mapping=None, retain_edge_coloring=True):
        """
        Given a coupling map and optionally some mapping between vertices of self.coupling_map
        and the given coupling map, this function creates a new SWAP strategy by embedding the
        existing SWAP strategy in the new coupling map. For instance, this allows us to use the
        line strategy in any coupling map that includes a line graph.

        Args:
            coupling_map: The new coupling map
            vertex_mapping: An optional mapping between vertices of the old and the new coupling
                map. If None, a trivial mapping (0 -> 0, 1 -> 1, etc.) is used
            retain_edge_coloring: Specifies whether edge coloring of old SWAP strategy should be
                used in the embedded strategy. Note that this can lead to an incomplete coloring
                in the new strategy.

        Returns:
            The new SWAP strategy obtained from embedding the existing SWAP strategy in the new
            coupling map
        """
        if coupling_map.size() < self.num_vertices:
            raise RuntimeError(
                f"Cannot embed SWAP strategy for coupling map with {self.num_vertices} "
                f"in coupling map with {coupling_map.size()} vertices."
            )

        if vertex_mapping is None:
            vertex_mapping = {i: i for i in range(self.num_vertices)}

        swap_layers = []
        for swap_layer in self.swap_layers:
            swap_layers.append(
                [(vertex_mapping[i], vertex_mapping[j]) for (i, j) in swap_layer]
            )

        if retain_edge_coloring and self.edge_coloring is not None:
            edge_coloring = {
                (vertex_mapping[i], vertex_mapping[j]): self.edge_coloring[(i, j)]
                for (i, j) in self.edge_coloring.keys()
            }
        else:
            edge_coloring = None

        return SwapStrategy(
            coupling_map=coupling_map,
            swap_layers=swap_layers,
            edge_coloring=edge_coloring,
        )


class LineSwapStrategy(SwapStrategy):
    """An optimal SWAP strategy for a line."""

    def __init__(self, line: List[int], num_swap_layers: int = None):
        """
        Creates a swap strategy for a line graph with the specified number of SWAP layers.
        This SWAP strategy will use the full line if instructed to do so (i.e. num_variables
        is None or equal to num_vertices). If instructed otherwise then the first num_variables
        nodes of the line will be used in the swap strategy.

        Args:
            line: A line given as a list of nodes, e.g. [0, 2, 3, 4].
            num_swap_layers: Number of swap layers the swap manager should be initialized with

        Returns:
            Swap strategy for the line graph
        """

        if num_swap_layers is None:
            num_swap_layers = len(line) - 2

        elif num_swap_layers < 0:
            raise ValueError(
                f"Negative number {num_swap_layers} passed for number of swap layers."
            )

        swap_layer0 = [(line[i], line[i + 1]) for i in range(0, len(line) - 1, 2)]
        swap_layer1 = [(line[i], line[i + 1]) for i in range(1, len(line) - 1, 2)]

        base_layers = [swap_layer0, swap_layer1]

        swap_layers = []
        for i in range(num_swap_layers):
            swap_layers.append(base_layers[i % 2])

        couplings = []
        for idx in range(len(line) - 1):
            couplings.append((line[idx], line[idx + 1]))
            couplings.append((line[idx + 1], line[idx]))

        super().__init__(
            coupling_map=CouplingMap(couplings),
            swap_layers=swap_layers,
            edge_coloring=line_coloring(num_vertices=len(line)),
        )


class FiveQubitTeeSwapStrategy(SwapStrategy):
    """A swap strategy for a coupling map of the form

    .. parsed-literal::

        0 -- 1 -- 2
             |
             3
             |
             4

    """

    def __init__(self):
        """Initialize the swap strategy."""

        swaps = [
            [(1, 3)],
            [(0, 1), (3, 4)],
            [(1, 3)],
        ]

        edges = [[0, 1], [1, 2], [1, 3], [3, 4]]

        coupling_map = CouplingMap(edges)
        coupling_map.make_symmetric()

        super().__init__(coupling_map, swaps)


class SevenQubitHeavySwapStrategy(SwapStrategy):
    """A swap strategy for a coupling map of the form

    .. parsed-literal::

        0 -- 1 -- 2
             |
             3
             |
        4 -- 5 -- 6

    """

    def __init__(self, n_qubits: int):
        """Initialize the swap strategy."""

        if n_qubits == 7:
            swaps = [
                [(0, 1), (3, 5)],
                [(1, 3), (4, 5)],
                [(0, 1), (3, 5)],
                [(1, 2), (5, 6)],
                [(3, 5)],
                [(1, 3), (5, 6)],
                [(3, 5)],
            ]

            edges = [[0, 1], [1, 2], [1, 3], [3, 5], [4, 5], [5, 6]]
        else:
            swaps = [
                [(0, 1), (3, 5)],
                [(1, 3), (4, 5)],
                [(0, 1), (3, 5)],
                [(1, 2)],
                [(3, 5)],
                [(1, 3)],
                [(3, 5)],
            ]

            edges = [[0, 1], [1, 2], [1, 3], [3, 5], [4, 5]]

        coupling_map = CouplingMap(edges)
        coupling_map.make_symmetric()

        super().__init__(coupling_map, swaps)


class DoubleRingSwapStrategy(SwapStrategy):
    """Full connectivity swap strategies for a coupling map of the form

    .. parsed-literal::

                       6                      17
                       |                       |
        0 -- 1 -- 4 -- 7 -- 10 -- 12 -- 15 -- 18 -- 21 -- 23
             |                     |                       |
             2                    13                      24
             |                     |                       |
             3 -- 5 -- 8 -- 11 -- 14 -- 16 -- 19 -- 22 -- 25 -- 26
                       |                       |
                       9                      20

    The swap layers and qubits used depend on the number of qubits. If the number of
    qubits is smaller than the length of the longest line then a longest line swap
    strategy should be used. For larger number of qubits this class will create the swap
    layers to apply. It also uses predefined swap layers and qubits to include which
    depend on the number of needed qubits.
    """

    def __init__(self, n_qubits: int) -> None:
        """Initialize the swap strategy.

        Args:
            n_qubits: The number of qubits for which to generate the swap strategy.

        Raises:
            QiskitError: If the number of qubits is smaller than 22 or larger then 27.
                In the first case a line swap strategy should be used and in the second
                case the backend does not have enough qubits.
        """

        self._lline = [
            0,
            1,
            2,
            3,
            5,
            8,
            11,
            14,
            16,
            19,
            22,
            25,
            24,
            23,
            21,
            18,
            15,
            12,
            10,
            7,
            6,
        ]

        # Create the longest line edges for the coupling map.
        # Forward direction
        self._longest_line_map = [
            [self._lline[idx], self._lline[idx + 1]]
            for idx in range(len(self._lline) - 1)
        ]

        # Backward direction
        self._longest_line_map += [
            [self._lline[idx + 1], self._lline[idx]]
            for idx in range(len(self._lline) - 1)
        ]

        # Defines the extra swaps to apply for a number of qubits.
        full_connectivity_strats = {
            22: {"n_line_layers": len(self._lline) + 3, "extra_swaps": {7: [(8, 9)]}},
            23: {
                "n_line_layers": len(self._lline) + 6,
                "extra_swaps": {7: [(8, 9), (19, 20)], 17: [(19, 20)]},
            },
            24: {
                "n_line_layers": len(self._lline) + 10,
                "extra_swaps": {7: [(8, 9), (19, 20)], 17: [(19, 20)]},
            },
            25: {
                "n_line_layers": len(self._lline) + 10,
                "extra_swaps": {
                    7: [(8, 9), (19, 20), (14, 13)],
                    17: [(8, 9), (19, 20)],
                },
            },
            26: {
                "n_line_layers": len(self._lline) + 10,
                "extra_swaps": {
                    7: [(8, 9), (19, 20), (14, 13)],
                    17: [(8, 9), (19, 20), (17, 18)],
                },
            },
            27: {
                "n_line_layers": len(self._lline) + 10,
                "extra_swaps": {
                    7: [(8, 9), (19, 20), (14, 13), (4, 1)],
                    17: [(8, 9), (19, 20), (17, 18), (4, 1)],
                },
            },
        }

        # The physical qubits to attach to the longest line.
        # The key is the number of required qubits and the value is the qubits
        # that will be added.
        self._qubits_to_add = {
            22: [9],
            23: [9, 20],
            24: [9, 20, 13],
            25: [9, 20, 13, 26],
            26: [9, 20, 13, 26, 17],
            27: [9, 20, 13, 26, 17, 4],
        }

        # The physical qubits used.
        self._qubits_used = self._lline + self._qubits_to_add[n_qubits]

        self._dangling_qubits_edges = {
            9: [(9, 8), (8, 9)],
            20: [(20, 19), (19, 20)],
            13: [(13, 14), (14, 13), (12, 13), (13, 12)],
            26: [(26, 25), (25, 26)],
            17: [(17, 18), (18, 17)],
            4: [(1, 4), (4, 1), (4, 7), (7, 4)],
        }

        # Create the swap strategy.
        super().__init__(
            self._make_coupling_map(n_qubits),
            self._create_swap_layers(**full_connectivity_strats[n_qubits]),
        )

    def _create_swap_layers(
        self, n_line_layers: int, extra_swaps: Dict[int, List[Tuple]]
    ) -> List[List[Tuple[int, int]]]:
        """Creates the swap layers for a given number of line layers and extra swaps.

        Args:
            n_line_layers: The number of layers of the line strategy to apply.
            extra_swaps: A dict where the swap layer index is the key and the value is a lis
                of swaps (specified as tuples to apply.)

        Returns:
            The swap layers to apply in the swap strategy.
        """

        # Swap gates on even edges, e.g. (0, 1), (2, 3)
        layer1 = [
            (self._lline[idx], self._lline[idx + 1])
            for idx in range(0, len(self._lline) - 1, 2)
        ]

        # Swap gates on odd edges, e.g. (1, 2)
        layer2 = [
            (self._lline[idx], self._lline[idx + 1])
            for idx in range(1, len(self._lline), 2)
        ]

        swap_strat = []
        for idx in range(n_line_layers):
            if idx % 2 == 0:
                swap_strat.append(layer1)
            else:
                swap_strat.append(layer2)

            if idx in extra_swaps:
                swap_strat.append(extra_swaps[idx])

        # The swap strategy above has been defined on the physical qubits for clarity but
        # for the transpiler pass to work we must define them on the virtual qubits.
        virtual_swaps = []
        for layer in swap_strat:
            virtual_swaps.append([])
            for swap in layer:
                pq0, pq1 = swap[0], swap[1]  # physical qubits
                virtual_swaps[-1].extend(
                    [(self.qubits_used.index(pq0), self.qubits_used.index(pq1))]
                )

        return virtual_swaps

    @property
    def qubits_used(self) -> List[int]:
        """Return the physical qubits that we use."""
        return self._qubits_used

    def _make_coupling_map(self, n_qubits: int) -> CouplingMap:
        """Make the coupling map that we will use."""

        # Add the extra edges to a copy of the longest line coupling map.
        coupling_map = [edge for edge in self._longest_line_map]
        for qubit in self._qubits_to_add[n_qubits]:
            for edge in self._dangling_qubits_edges[qubit]:
                coupling_map.append(edge)

        # The coupling map has been defined on the physical qubits for clarity
        # however the swap strategy works with virtual qubits so we remap to virtual
        virtual_map = []
        for edge in coupling_map:
            pq0, pq1 = edge[0], edge[1]  # physical qubits
            virtual_map.extend(
                [(self.qubits_used.index(pq0), self.qubits_used.index(pq1))]
            )

        return CouplingMap(virtual_map)


def get_swap_strategy(
    backend_name: str, n_qubits: Optional[int] = None
) -> Tuple[SwapStrategy, List[int]]:
    """Get a swap strategy and the mapping based on the backend.

    Args:
        backend_name: the name of the backend as a string.
        n_qubits: the number of qubits to use. If not specified then all qubits will be used.

    Returns:
        A tuple where the first element is a swap strategy for the given backend and the second
        element is the list of physical qubits that the swap strategy applies to.
    """

    if backend_name in [
        "ibmq_belem",
        "ibmq_quito",
        "ibmq_lime",
        "fake_belem",
        "fake_quito",
        "fake_lime",
    ]:
        return FiveQubitTeeSwapStrategy(), list(range(5))

    if backend_name in [
        "fake_lagos",
        "ibm_lagos",
        "ibmq_casablanca",
        "ibm_nairobi",
        "ibmq_jakarta",
    ]:
        return SevenQubitHeavySwapStrategy(n_qubits), list(range(n_qubits))

    if backend_name in ["ibmq_santiagio", "ibmq_bogota", " ibmq_manila"]:
        return LineSwapStrategy(list(range(5))), list(range(5))

    devices_27q = [
        "ibmq_montreal",
        "ibmq_mumbai",
        "ibmq_kolkata",
        "ibmq_dublin",
        "ibm_cairo",
        "ibm_hanoi",
        "ibmq_toronto",
        "ibmq_sydney",
        "fake_montreal",
        "fake_mumbai",
        "fake_kolkata",
        "fake_dublin",
        "fake_cairo",
        "fake_hanoi" "ibmq_toronto",
        "fake_sydney",
    ]

    if backend_name in devices_27q:
        strat = DoubleRingSwapStrategy(n_qubits)
        return strat, strat.qubits_used

    raise ValueError(f"No swap strategy found for {backend_name}")


class HWQAOAAnsatz(QAOAAnsatz):
    """Class for a hardware efficient QAOAAnsatz."""

    def __init__(
        self,
        cost_operator=None,
        reps: int = 1,
        initial_state=None,
        mixer_operator=None,
        name: str = "QAOA",
        swap_strategy: SwapStrategy = None,
        initial_layout: Layout = None,
    ):
        r"""
        Args:
            cost_operator (OperatorBase, optional): The operator representing the cost of
                the optimization problem, denoted as :math:`U(C, \gamma)` in the original paper.
                Must be set either in the constructor or via property setter.
            reps (int): The integer parameter p, which determines the depth of the circuit,
                as specified in the original paper, default is 1.
            initial_state (QuantumCircuit, optional): An optional initial state to use.
                If `None` is passed then a set of Hadamard gates is applied as an initial state
                to all qubits.
            mixer_operator (OperatorBase or QuantumCircuit, optional): An optional custom mixer
                to use instead of the global X-rotations, denoted as :math:`U(B, \beta)`
                in the original paper. Can be an operator or an optionally parameterized quantum
                circuit.
            name (str): A name of the circuit, default 'qaoa'
            swap_strategy (SwapStrategy): The SWAP strategy used for insertion of SWAP layers
            initial_layout (Layout): The initial layout mapping logical to physical qubits. If not
                specified, a trivial initial layout is used
        """
        self._num_logical_qubits = None
        self._num_physical_qubits = None
        self._swapped_layout = None
        self._cost_matrix = None

        super().__init__(
            cost_operator=cost_operator,
            reps=reps,
            initial_state=initial_state,
            mixer_operator=mixer_operator,
            name=name,
        )

        self.swap_strategy = swap_strategy
        self.initial_layout = initial_layout

    @property
    def final_layout(self) -> Layout:
        """
        Returns:
            Returns a Layout object representing the layout after application of the
            mapped QAOA circuit.
        """
        if self.reps % 2 == 0:
            return self.initial_layout
        else:
            return self._swapped_layout

    @property
    def num_qubits(self) -> int:
        """
        The number of qubits in the circuit. This is given as the number of physical qubits, i.e.
        the size of the coupling map the QAOA circuit is mapped to. If no SWAP strategy and
        therefore no coupling map is specified, this defaults to the number of logical qubits.
        Returns 0 if no cost operator has been set yet.

        Returns:
            The number of qubits
        """
        if self._num_physical_qubits is not None:
            return self._num_physical_qubits
        elif self._num_logical_qubits is not None:
            return self._num_logical_qubits
        else:
            return 0

    @property
    def cost_operator(self):
        """Returns an operator representing the cost of the optimization problem.

        We need to override the cost_operator property to set the cost_matrix accordingly.

        Returns:
            OperatorBase: cost operator.
        """
        return self._cost_operator

    @cost_operator.setter
    def cost_operator(self, cost_operator: Optional[OperatorBase]) -> None:
        """
        Sets cost operator.
        Args:
            cost_operator: cost operator to set.
        """
        self._cost_operator = cost_operator
        self._invalidate()
        self._num_logical_qubits = cost_operator.num_qubits if cost_operator else None
        self._cost_matrix = (
            self._get_cost_matrix(cost_operator) if cost_operator else None
        )

    @property
    def swap_strategy(self) -> Optional[SwapStrategy]:
        """Returns the swap strategy used for mapping the circuit to a coupling map."""
        return self._swap_strategy

    @swap_strategy.setter
    def swap_strategy(self, swap_strategy: Optional[SwapStrategy]) -> None:
        """Sets the swap strategy used for mapping the circuit to a coupling map."""
        self._swap_strategy = swap_strategy
        self._num_physical_qubits = (
            swap_strategy.num_vertices if swap_strategy else None
        )
        self._invalidate()

    @property
    def initial_layout(self) -> Optional[Layout]:
        """Returns the initial layout (mapping of physical to logical qubits) of the circuit."""
        return self._initial_layout

    @initial_layout.setter
    def initial_layout(self, initial_layout: Optional[Layout]) -> None:
        """Sets the initial layout (mapping of physical to logical qubits)."""
        self._initial_layout = initial_layout
        self._invalidate()

    @staticmethod
    def _get_cost_matrix(cost_operator: OperatorBase) -> np.array:
        """Returns the cost matrix of a cost operator

        Args:
            cost_operator: An operator representing the cost of an optimization problem.

        Returns:
            The corresponding cost matrix as a nested list.
        """
        # TODO: Add check for cost operator?
        quadratic_program = QuadraticProgram()
        quadratic_program.from_ising(qubit_op=cost_operator)
        size = len(quadratic_program.variables)
        objective = quadratic_program.objective
        matrix = objective.quadratic.to_array(symmetric=True)
        linear_coeff = objective.linear.to_array()

        for i in range(size):
            matrix[i][i] += linear_coeff[i]

        return matrix

    def _check_configuration(self, raise_on_failure: bool = True) -> bool:
        """Check if the current configuration allows the circuit to be built.

        Args:
            raise_on_failure: If True, raise if the configuration is invalid. If False, return
                False if the configuration is invalid.

        Returns:
            True, if the configuration is valid. Otherwise, depending on the value of
            ``raise_on_failure`` an error is raised or False is returned.
        """
        # Check standard QAOA configuration requirements
        if not super()._check_configuration(raise_on_failure=raise_on_failure):
            return False

        if self.swap_strategy is not None and self.cost_operator is not None:
            # Check that circuit can be mapped to coupling map of specified SWAP strategy
            if self._num_logical_qubits > self._num_physical_qubits:
                if raise_on_failure:
                    raise AttributeError(
                        f"Cannot map a circuit with {self._num_logical_qubits} qubits to "
                        f"a physical device with {self._num_physical_qubits} qubits."
                    )
                return False

        # Check that initial layout is compatible with coupling map and that process terminates!

        # 1) build all possible connections that the swap strategy builds.
        possible_edges = set()
        for swap_layer_idx in range(len(self._swap_strategy) + 1):
            for edge in self._swap_strategy.swapped_coupling_map(
                swap_layer_idx
            ).get_edges():
                possible_edges.add(edge)

        # 2) Get a list of Pauli strings in the operator, e.g. ["IIZZ", "ZIIZ"]
        pauli_strings = []
        for ops in self.operators:
            pauli_strings.extend([str(pauli) for pauli in ops.primitive.paulis])

        # 3) Convert the strings to edges.
        required_edges = set()
        for pauli_str in pauli_strings:
            edge = tuple([i for i, p in enumerate(pauli_str[::-1]) if p != "I"])

            if len(edge) == 2:
                required_edges.add(edge)

            if len(edge) > 2:
                if raise_on_failure:
                    raise ValueError(
                        f"The Pauli {pauli_str} is non-local (i.e. has more than 2 Z-terms)."
                    )

                return False

        # 4) Check that the swap strategy supports all required edges
        for edge in required_edges:
            if edge not in possible_edges:
                if raise_on_failure:
                    raise ValueError(
                        f"The edge {edge} is not supported by the SWAP strategy "
                        f"{self.swap_strategy} which creates edges {possible_edges}."
                    )

                return False

        return True

    def _build(self) -> None:
        """Build the circuit."""

        # If the _data property is set the circuit has already been built
        if self._data is not None:
            return

        # Default to standard QAOAAnsatz if no SWAP strategy has been set
        if self.swap_strategy is None:
            super()._build()
            return

        self._check_configuration()
        self._data = []

        # Set the registers
        try:
            qr = QuantumRegister(self.num_qubits, "q")
            self.add_register(qr)
        except CircuitError:
            # The register already exists, probably because of a previous composition
            pass

        # Set initial layout to trivial layout if not set
        if self._initial_layout is None:
            self._initial_layout = Layout.generate_trivial_layout(*self.qregs)

        # Order qubit pairs by the minimal number of steps after which they are adjacent during
        # the SWAP process, i.e. by the SWAP layer depth after which the corresponding
        # interaction can be applied
        distance_matrix = self.swap_strategy.distance_matrix
        gate_layers = {}
        for i in range(self._num_logical_qubits):
            for j in range(i):

                rotation_angle = self._cost_matrix[i][j]

                if np.isclose(rotation_angle, 0):
                    continue

                distance = distance_matrix[
                    self.initial_layout.get_virtual_bits()[self.qubits[i]]
                ][self.initial_layout.get_virtual_bits()[self.qubits[j]]]

                if distance not in gate_layers.keys():
                    gate_layers[distance] = {(i, j): rotation_angle}
                else:
                    gate_layers[distance][(i, j)] = rotation_angle

        max_distance = max(gate_layers.keys())
        final_permutation = self.swap_strategy.composed_permutation(idx=max_distance)
        self._swapped_layout = Layout()
        self._swapped_layout.from_dict(
            {
                self.initial_layout.get_physical_bits()[i]: final_permutation[i]
                for i in range(self._num_physical_qubits)
            }
        )

        # Apply QAOA layers
        qaoa_circuit = QuantumCircuit(*self.qregs, name=self.name)
        parameters = ParameterVector("t", 2 * self.reps)
        for i in range(self.reps):
            qaoa_circuit.compose(
                self._mapped_qaoa_layer(
                    mixer_parameter=parameters[2 * i + 1],
                    cost_parameter=parameters[2 * i],
                    rzz_layers=gate_layers,
                    reverse_ops=(i % 2 == 1),
                ),
                inplace=True,
            )

        # Prepend an initial state (defaults to the equal superposition state if not specified)
        if self.initial_state:
            qaoa_circuit.compose(
                self.initial_state,
                front=True,
                inplace=True,
                qubits=list(range(self._num_logical_qubits)),
            )

        try:
            instr = qaoa_circuit.to_gate()
        except QiskitError:
            instr = qaoa_circuit.to_instruction()

        self.append(instr, self.qubits)

    def _mapped_qaoa_layer(
        self, mixer_parameter, cost_parameter, rzz_layers, reverse_ops=False
    ) -> QuantumCircuit:
        """
        Creates a single mapped QAOA layer with specified parameters and rzz_layers. The mapped
        circuit consists of alternating RZZ and SWAP layers.

        Args:
            mixer_parameter: Parameter to use for mixer layer
            cost_parameter: Parameter to use for cost layer
            rzz_layers: RZZ layers specified as a dictionary with integer keys corresponding to the
                layer index and values corresponding to the RZZ gates in the layer. RZZ gates are
                specified as dictionaries with integer tuples specifying the corresponding qubit
                pairs as keys and rotational angles as values.
            reverse_ops: Reverses the QAOA layer by reversing the order of the instructions. This
                allows us to alternate between even and odd layers.

        Returns:
            The mapped QAOA layer as a quantum circuit
        """

        # Build the layer for the cost Hamiltonian
        qaoa_cost_layer = QuantumCircuit(self._num_physical_qubits)

        # Applying Ising gates for single qubit rotations
        for j in range(self._num_logical_qubits):
            rotation_angle = 0
            for k in range(self._num_logical_qubits):
                rotation_angle -= self._cost_matrix[j][k]
                rotation_angle -= self._cost_matrix[k][j]

            if abs(rotation_angle) > 1.0e-14:
                qaoa_cost_layer.rz(rotation_angle * cost_parameter, j)

        # Iterate over and apply gate layers
        max_distance = max(rzz_layers.keys())
        current_layout = Layout()
        for i in range(max_distance + 1):
            # Set the current layout depending on the number of SWAP layers already applied
            current_permutation = self.swap_strategy.composed_permutation(idx=i)
            current_layout.from_dict(
                {
                    self.initial_layout.get_physical_bits()[j]: current_permutation[j]
                    for j in range(self._num_physical_qubits)
                }
            )
            # Determine SWAP gates in upcoming SWAP layer
            try:
                upcoming_swaps = copy.copy(self.swap_strategy.swap_layers[i])
            except IndexError:
                upcoming_swaps = []

            # Get current layer and replace the problem indices j,k by the corresponding
            # positions in the coupling map
            rzz_layer = rzz_layers.get(i, {})
            rzz_layer = {
                (
                    current_layout.get_virtual_bits()[self.qubits[j]],
                    current_layout.get_virtual_bits()[self.qubits[k]],
                ): rotation_angle
                for (j, k), rotation_angle in rzz_layer.items()
            }

            # Build a list of RZZ gates that overlap with next SWAP layer and should be applied at
            # the end of the current RZZ layer to cancel as many CNOT gates as possible.
            final_sublayer = {}
            layer_new = {}
            for (j, k), rotation_angle in rzz_layer.items():
                if (j, k) in upcoming_swaps:
                    final_sublayer[(j, k)] = rotation_angle
                    upcoming_swaps.remove((j, k))
                if (k, j) in upcoming_swaps:
                    final_sublayer[(j, k)] = rotation_angle
                    upcoming_swaps.remove((k, j))
                else:
                    layer_new[(j, k)] = rotation_angle
            rzz_layer = layer_new

            # Build sub layers according to graph coloring or greedily if no graph
            # coloring has been specified TODO: outsource this to a single function?
            edge_coloring = self.swap_strategy.edge_coloring
            if edge_coloring is not None:
                sublayers = [{} for _ in range(max(edge_coloring.values()) + 1)]
                for edge, rotation_angle in rzz_layer.items():
                    sublayers[edge_coloring[edge]][edge] = rotation_angle
            else:
                sublayers = []
                while rzz_layer:
                    current_layer = {}
                    remaining_gates = {}
                    blocked_vertices = set()
                    for edge, rotation_angle in rzz_layer.items():
                        if all([j not in blocked_vertices for j in edge]):
                            current_layer[edge] = rotation_angle
                            blocked_vertices = blocked_vertices.union(edge)
                        else:
                            remaining_gates[edge] = rotation_angle
                    rzz_layer = remaining_gates
                    sublayers.append(current_layer)

            # Apply sub-layers
            for sublayer in sublayers:
                for edge, rotation_angle in sublayer.items():
                    (j, k) = map(
                        lambda vertex: self.initial_layout.get_physical_bits()[vertex],
                        edge,
                    )
                    qaoa_cost_layer.cx(j, k)
                    qaoa_cost_layer.rz(rotation_angle * cost_parameter, k)
                    qaoa_cost_layer.cx(j, k)

            # Apply final sublayer
            for edge, rotation_angle in final_sublayer.items():
                (j, k) = map(
                    lambda vertex: self.initial_layout.get_physical_bits()[vertex], edge
                )
                qaoa_cost_layer.cx(j, k)
                qaoa_cost_layer.rz(rotation_angle * cost_parameter, k)

                # Add a swap if we are not at the end
                if i < max_distance:
                    qaoa_cost_layer.cx(k, j)
                    qaoa_cost_layer.cx(j, k)
                else:
                    qaoa_cost_layer.cx(j, k)

            # Apply SWAP gates
            if i < max_distance:
                for swap in upcoming_swaps:
                    (j, k) = map(
                        lambda vertex: self.initial_layout.get_physical_bits()[vertex],
                        swap,
                    )
                    qaoa_cost_layer.cx(j, k)
                    qaoa_cost_layer.cx(k, j)
                    qaoa_cost_layer.cx(j, k)

        # Possibly reverse cost layer and apply mixer Hamiltonian to correct qubits
        if reverse_ops:
            qaoa_layer = qaoa_cost_layer.reverse_ops()
            for i in range(self._num_logical_qubits):
                qaoa_layer.rx(2.0 * mixer_parameter, i)
        else:
            qaoa_layer = qaoa_cost_layer
            for i in range(self._num_logical_qubits):
                idx = self.initial_layout.get_physical_bits()[
                    self._swapped_layout.get_virtual_bits()[self.qubits[i]]
                ]
                qaoa_layer.rx(2.0 * mixer_parameter, idx)

        return qaoa_layer


class QAOASwapPass(TransformationPass):
    """A transpiler pass for QAOA circuits."""

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Replace all QAOAGates with a hardware efficient implementation of QAOA.

        Args:
            dag: The DAG to run the transpiler on.

        Returns:
            The DAG with :class:`~qiskit.circuit.library.n_local.qaoa_ansatz.QAOAGate`s
            replaced by a hardware efficient implementation.
        """

        current_layout = self.property_set.get("layout", None)
        if current_layout is None:
            current_layout = Layout().generate_trivial_layout(*dag.qregs.values())

        swap_strategy = self.property_set.get("qaoa_swap_strategy", None)
        if swap_strategy is None:
            warn(
                f"{self.__class__.__name__} did not do anything as no swap strategy was found."
            )

            return dag

        for node in dag.op_nodes():
            op = node.op
            if isinstance(op, QAOAGate):
                # Generate initial layout for the qubits the QAOA is run on
                qaoa_layout = Layout()
                qaoa_layout.from_dict(
                    {qubit: current_layout[qubit] for qubit in node.qargs}
                )

                # Create and insert the hardware efficient QAOA in the DAG
                qaoa = HWQAOAAnsatz(
                    cost_operator=op.cost_operator,
                    reps=op.reps,
                    initial_state=op.initial_state,
                    mixer_operator=op.mixer_operator,
                    swap_strategy=swap_strategy,
                    initial_layout=qaoa_layout,
                )

                # Reassign the parameters to those of the original circuit.
                rebound = qaoa.assign_parameters(op.params)

                dag.substitute_node_with_dag(node, circuit_to_dag(rebound.decompose()))

        mapping = self.property_set.get("qaoa_swap_layout", None)
        if mapping is not None:
            self.property_set["layout"] = Layout.from_intlist(
                mapping, *dag.qregs.values()
            )

        return dag


class SwapStrategyCreator(AnalysisPass):
    """Create the swap strategy and mapping to physical qubits for QAOA.

    This class analyses the coupling map to first see if a line swap strategy can be used.
    The best line is determined based on the fidelity of the two-qubit gates. If the backend
    has enough qubits but no simple path can be found (i.e. no line) then a swap strategy
    from the swap strategy library is used.
    """

    def __init__(
        self,
        backend: Backend,
        two_qubit_gate: str = "cx",
        use_fidelity: bool = True,
        swap_strategy: Optional[SwapStrategy] = None,
        swap_strategy_qubits: Optional[List[int]] = None,
    ):
        """
        Args:
            backend: The backend that we will analyze.
            two_qubit_gate: The name of the two-qubit gate of the backend.
            use_fidelity: Whether or not to use the fidelity of the two-qubit gate
                to determine the best path. By default this variable is set to True.
            swap_strategy: The swap strategy to use. If this variable is not given (i.e.
                the default) then the swap strategy will be created based on the problem
                size and optionally the gate fidelity. If this variable is given then the
                swap_strategy_qubits variable must also be given.
            swap_strategy_qubits: A list of integers representing the physical qubits
                to run on. If this list is None (the default value) then the qubits
                will be determined based on the problem size and optionally the fidelity
                of the two-qubit gates.
        """
        super().__init__()

        coupling_map = backend.configuration().coupling_map

        if coupling_map is None:
            raise QiskitError(
                "Cannot create a swap strategy if the backend does not have a coupling map."
            )

        self._coupling_map = CouplingMap(coupling_map)
        self._two_qubit_fidelity = {}
        self._max_problem_size = backend.configuration().num_qubits
        self._name = backend.name
        self._use_fidelity = use_fidelity

        props = backend.properties()
        for edge in coupling_map:
            self._two_qubit_fidelity[tuple(edge)] = 1 - props.gate_error(
                two_qubit_gate, edge
            )

        if swap_strategy is not None and swap_strategy_qubits is not None:
            self._swap_strategy = swap_strategy
            self._path = swap_strategy_qubits
        elif swap_strategy is None and swap_strategy_qubits is None:
            self._swap_strategy = None
            self._path = None
        else:
            raise QiskitError(
                "Either both swap_strategy and swap_strategy_qubits are None or neither are None."
            )

    def find_path(self, length: int) -> Optional[List[int]]:
        """Find the paths of the coupling map with the appropriate length.

        Args:
            length: The length of the simple path to find.

        Returns:
            The best path that could be found. If no path was found then None is returned.
        """

        paths, size = [], self._coupling_map.size()

        for node1 in range(size):
            for node2 in range(node1 + 1, size):
                paths.extend(
                    rx.all_simple_paths(
                        self._coupling_map.graph,
                        node1,
                        node2,
                        min_depth=length,
                        cutoff=length,
                    )
                )
        if len(paths) == 0:
            return None

        if not self._use_fidelity:
            return paths[0]

        fidelities = [self.evaluate_path(path) for path in paths]

        return self.get_best_path(paths, fidelities)

    @staticmethod
    def get_best_path(paths: List[List[int]], fidelities: List[float]) -> List[int]:
        """Sort the paths according to their fidelity.

        Args:
            paths: The paths on the qubits. Each sublist is a path.
            fidelities: The fidelity for each path.

        Returns:
            The paths sorted by fidelity. The highest fidelity path is at index 0.
        """

        return min(zip(paths, fidelities), key=lambda x: -x[1])[0]

    def evaluate_path(self, path: List[int]) -> float:
        """Compute the fidelity of the path.

        This function uses a heuristic to compute the fidelity of the two-qubit gates on the given
        path by multiplying the fidelity of all two-qubit gates on the path.

        Args:
            path: The path as a list of qubits.

        Returns:
            The fidelity of the path as the product of gate fidelities.
        """
        if not path or len(path) == 1:
            return 0.0

        fidelity = 1.0
        for idx in range(len(path) - 1):
            fidelity *= self._two_qubit_fidelity[(path[idx], path[idx + 1])]

        return fidelity

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """create a swap strategy on the coupling map for the given problem size.

        First, we try and find a line that can accommodate problems of the given size.
        If no such line is found use the full swap strategy for the coupling map taken from
        the library of swap strategies. The swap strategy and path are saved in the property
        set of the pass manager.

        Args:
            dag: the number of qubits in the dag determines the problem size.
        """

        if self._swap_strategy is None or self._path is None:
            problem_size = dag.num_qubits()

            if problem_size > self._max_problem_size:
                raise ValueError(
                    f"{self._name} can only handle problems up to size "
                    f"{self._max_problem_size}. Received {problem_size}"
                )

            self._path = self.find_path(problem_size)

            if self._path is None:
                self._swap_strategy, self._path = get_swap_strategy(
                    self._name, problem_size
                )
            else:
                self._swap_strategy = LineSwapStrategy(list(range(len(self._path))))

        self.property_set["qaoa_swap_strategy"] = self._swap_strategy
        self.property_set["qaoa_swap_layout"] = self._path

        return dag


class InitialQubitMapper(TransformationPass):
    """Reorder the decision variables based on the swap strategy.

    This class iteratively reorders the decision variables in a PauliSumOp based on
    a swap strategy to reduce the number of two-qubit operations. The swap strategy
    defines a matrix of distances :math:`d_{i,j}` that corresponds to the distance
    measured in number of swap layers between qubit :math:`i` and :math:`j`. For
    example, adjacent qubits in the coupling map have a distance of 0 and next-nearest
    neighbours have a distance of 1 if the next swap layer connects them. At each
    iteration, the virtual qubit with the largest sum product of distances and pauli
    pre-factors to the virtual qubits that have already been mapped to physical qubits
    is the next qubit to be mapped. For this qubit, we then identify the unmapped
    physical qubit in the coupling map that minimizes the sum-product of distances
    and pauli pre-factors.
    """

    def permute_operator(
        self, cost_op: PauliSumOp, swap_strategy: SwapStrategy
    ) -> PauliSumOp:
        """Permute the Paulis in cost_op to minimize the number of CNOT gates when swapping.

        This is the main method of this class. It permutes the operators in the given
        cost_op according to the distance matrix of the swap strategy. This helps reduce
        the number of CNOT gates that will be needed when applying the swap strategy. This
        is only needed for sparse cost operators.

        Args:
            cost_op: The cost operator for which to create the mapping based on the
                swap_strategy stored in the mapper.
            swap_strategy: The swap strategy that provides the distance matrix.

        Returns:
            The permuted cost operator.

        Raises:
            QiskitError: if the cost operator is too large for the swap strategy.
        """
        if len(swap_strategy.distance_matrix) < cost_op.num_qubits:
            raise QiskitError(
                f"The cost operator with {cost_op.num_qubits} qubits is too large "
                f"for the swap strategy {swap_strategy}."
            )

        rotation_angles = self._map_rotation_angles(cost_op)

        # A mapping with the logical qubit as key and the physical qubit as value.
        physical_mapping = dict()

        # The distance matrix between the qubits in the swap strategy.
        distance_mat = swap_strategy.distance_matrix

        unmapped_virtual_qubits = set(range(cost_op.num_qubits))
        unmapped_physical_qubits = set(range(cost_op.num_qubits))

        while unmapped_virtual_qubits:

            # Get the next virtual qubit to map using the sum of rotations to the mapped qubits.
            v_qubit = self._get_next_qubit_to_map(
                list(unmapped_virtual_qubits), physical_mapping, rotation_angles
            )

            # Find the physical qubit to which to map the virtual qubit.
            p_qubit = self._min_distance(
                v_qubit,
                physical_mapping,
                unmapped_physical_qubits,
                rotation_angles,
                distance_mat,
            )

            # Update state variables.
            physical_mapping[v_qubit] = p_qubit
            unmapped_virtual_qubits.remove(v_qubit)
            unmapped_physical_qubits.remove(p_qubit)

        # reorder data to get a permutations list
        permutation = [0] * cost_op.num_qubits
        for v_qubit, p_qubit in physical_mapping.items():
            permutation[v_qubit] = p_qubit

        return copy.deepcopy(cost_op).permute(permutation)

    def _min_distance(
        self,
        qubit: int,
        physical_mapping: Dict[int, int],
        free_positions: Set[int],
        rotation_angles: Dict[Tuple, float],
        distance_mat: List[List[int]],
    ) -> int:
        r"""Find the physical qubit to which to map the virtual qubit.

        The cost function that is computed is

        .. math::

            \sum_{j\in M} d_{v, v(j)}\theta_{ij}.

        Here, :math:`d_{v, v(j)}` is the swap distance between the physical node v
        and the position of the physical qubit :math:`v(j)` to which decision variable
        :math:`j` has been mapped. :math:`\theta_{ij}` is the angle between the
        decision variable to map, i.e. :math:`i`, and the mapped decision variable :math:`j`.
        The set :math:`M` is the set of decision variables that have already been mapped
        to a physical qubit.

        Args:
            qubit: The decision variable to map, i.e. :math:`i`.
            physical_mapping: The dictionary of decisions variables (i.e. virtual qubits) as keys
                that have already been mapped to physical variables as values.
            rotation_angles: A dict connecting the decision variables to their corresponding
                rotations. E.g. 4.0*ZIIZ has rotation_angles {(0, 3): 4.0, (3, 0): 4.0}.
            distance_mat: The distance matrix from the swap strategy to use.

        Returns:
            The index of the physical qubit to which the decision variable (i.e. the qubit)
            argument will be mapped.
        """
        smallest_cost, smallest_idx = np.Inf, None

        def calculate_cost(pos):
            # Compute the sum in the cost function to minimize
            cost = 0.0
            for v_qubit, p_qubit in physical_mapping.items():
                theta = rotation_angles.get((qubit, v_qubit), 0)
                cost += distance_mat[pos][p_qubit] * theta
            return cost

        return min(free_positions, key=calculate_cost)

    @staticmethod
    def _map_rotation_angles(cost_op: PauliSumOp) -> Dict[Tuple, float]:
        """Return the rotation angle between two qubits.

        Args:
            cost_op: A sum of Paulis whose coefficients determine the rotation angles
                that will be extracted and put into a dict.

        Returns:
            A dictionary where the keys are the decision variable indices, e.g. (2, 3)
            and the values are the coefficients of the corresponding pauli Z terms.
            The returned dictionary contains keys (A, B) and (B, A) which both point
            to the same rotation angle since the RZZGate is symmetric.
        """

        rotation_angles = dict()

        for pauli, coeff in zip(cost_op.primitive.paulis, cost_op.primitive.coeffs):
            indices = tuple([idx for idx, char in enumerate(pauli) if str(char) == "Z"])

            rotation_angles[indices] = coeff
            rotation_angles[indices[::-1]] = coeff

        return rotation_angles

    def _get_next_qubit_to_map(
        self,
        unmapped: List[int],
        mapped: Dict[int, int],
        rotation_angles: Dict[Tuple, float],
    ) -> int:
        """Return the next virtual qubit to map to a physical qubit.

        Args:
            unmapped: Qubits that have not yet been mapped to a physical qubit
                in the initial layout.
            mapped: The dictionary of decisions variables (i.e. virtual qubits) as keys
                that have already been mapped to physical variables as values.
            rotation_angles: A dict connecting the decision variables to their corresponding
                rotations. E.g. 4.0*ZIIZ has rotation_angles {(0, 3): 4.0, (3, 0): 4.0}.

        Returns:
            A list of sum of rotations between apped and unmapped qubits.
        """

        # If no qubit has been mapped we first consider the qubit with the highest
        # number of connections.
        if not mapped:
            max_rotation_count = 0
            max_qubit = 0
            for idx1, qb1 in enumerate(unmapped):

                rotation_count = 0
                for idx2, qb2 in enumerate(unmapped[idx1 + 1 :]):
                    if (idx1, idx2) in rotation_angles:
                        rotation_count += 1

                if rotation_count > max_rotation_count:
                    max_qubit = qb1

            return max_qubit

        # Consider the following qubits using the largest som of rotations.
        sum_of_rotations = [
            self._rotation_sum(qubit, list(mapped.keys()), rotation_angles)
            for qubit in unmapped
        ]

        return max(zip(sum_of_rotations, unmapped), key=lambda x: x[0])[1]

    @staticmethod
    def _rotation_sum(
        qubit: int, other_qubits: List[int], rotation_angles: Dict[Tuple, float]
    ) -> float:
        """Compute the rotation sum between the given qubit and the other qubits.

        Args:
            qubit: The qubit for which we compute the sum of all other rotation angles.
            other_qubits: The list of qubits that have already been mapped to physical
                qubits.

        Returns:
            The sum of the rotation angles between the given qubit and the unmapped qubit.
        """
        return sum(rotation_angles.get((qubit, other), 0) for other in other_qubits)

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Reorder the terms in the QAOA cost operator according to a swap strategy.

        This pass does not modify the circuit but simply reorders the terms in the cost
        operator of any QAOA gates.

        Args:
            dag: The DAG to run the transpiler on.

        Returns:
            The DAG in which the :class:`~qiskit.circuit.library.n_local.qaoa_ansatz.QAOAGate`s
            cost operators have been remapped.
        """

        swap_strategy = self.property_set.get("qaoa_swap_strategy", None)
        if swap_strategy is None:
            warn(
                f"{self.__class__.__name__} did not do anything as no swap strategy was found."
            )

            return dag

        for node in dag.op_nodes(QAOAGate):
            op = node.op
            op.cost_operator = self.permute_operator(op.cost_operator, swap_strategy)

        return dag


def swap_pass_manager_creator(
    backend,
    swap_strategy: Optional[SwapStrategy] = None,
    swap_strategy_qubits: Optional[List[int]] = None,
    use_initial_mapping: bool = False,
) -> PassManager:
    """Create a swap strategy pass manager.

    Args:
        backend: The backend for which to create the swap strategy pass manager.
        swap_strategy: An optional swap strategy that lets users pass in swap strategies
            instead of using the default methodology in the :class:`SwapStrategyCreator`.
        swap_strategy_qubits: The list of physical qubits that are involved in the swap strategy.
            This variable must also be given if the swap_strategy variable is not None.
        use_initial_mapping: If True (the default is false), add an initial
            mapping to the transpilation passes that will reorganize the Pauli operations in
            the cost operator to reduce the number of two-qubit gates that the SWAP strategy will
            implement.
    """

    if swap_strategy is not None and swap_strategy_qubits is None:
        warn("swap_strategy will be ignored since swap_strategy_qubits is None.")

    basis_gates = backend.configuration().basis_gates

    swap_pm = PassManager()
    swap_pm.append(
        SwapStrategyCreator(
            backend,
            swap_strategy=swap_strategy,
            swap_strategy_qubits=swap_strategy_qubits,
        )
    )

    if use_initial_mapping:
        swap_pm.append(InitialQubitMapper())

    coupling_map = CouplingMap(backend.configuration().coupling_map)

    swap_pm.append(
        [
            QAOASwapPass(),
            FullAncillaAllocation(coupling_map),
            EnlargeWithAncilla(),
            ApplyLayout(),
            UnrollCustomDefinitions(std_eqlib, basis_gates),
            BasisTranslator(std_eqlib, basis_gates),
            Optimize1qGatesDecomposition(basis_gates),
        ]
    )

    return swap_pm


def pulse_pass_creator(backend) -> PassManager:
    """Create a pass manager for pulse-efficient transpilation.

    Args:
        backend: The backend for which to create the passes.

    Returns:
        The pulse efficient pass manager.
    """
    rzx_basis = ["rzx", "rz", "x", "sx"]
    # a collection of passes to build the pulse-efficient pass manager.
    pulse_efficient_passes = [
        # Consolidate consecutive two-qubit operations.
        Collect2qBlocks(),
        ConsolidateBlocks(basis_gates=["rz", "sx", "x", "rxx"]),
        # Rewrite circuit in terms of Weyl-decomposed echoed RZX gates.
        EchoRZXWeylDecomposition(backend.defaults().instruction_schedule_map),
        # Attach scaled CR pulse schedules to the RZX gates.
        RZXCalibrationBuilderNoEcho(backend),
        # Simplify single-qubit gates.
        UnrollCustomDefinitions(std_eqlib, rzx_basis),
        BasisTranslator(std_eqlib, rzx_basis),
        Optimize1qGatesDecomposition(rzx_basis),
    ]
    return PassManager(pulse_efficient_passes)


def main(backend, user_messenger, **kwargs):
    """Entry function."""
    # parse inputs
    mandatory = {"operator"}
    missing = mandatory - set(kwargs.keys())
    if len(missing) > 0:
        raise ValueError(f"The following mandatory arguments are missing: {missing}.")

    # Extract the input form the kwargs and build serializable kwargs for book keeping.
    serialized_inputs = {}
    operator = kwargs["operator"]

    if not isinstance(operator, PauliSumOp):
        try:
            operator = PauliSumOp.from_list([(str(operator), 1)])
        except QiskitError as err:
            raise QiskitError(
                f"Cannot convert {operator} of type {type(operator)} to a PauliSumOp."
            ) from err

    serialized_inputs["operator"] = operator.primitive.to_list()

    aux_operators = kwargs.get("aux_operators", None)
    if aux_operators is not None:
        serialized_inputs["aux_operators"] = []
        for op in aux_operators:
            if not isinstance(op, PauliSumOp):
                try:
                    op = PauliSumOp.from_list([(str(op), 1)])
                except QiskitError as err:
                    raise QiskitError(
                        f"Cannot convert {op} of type {type(op)} to a PauliSumOp"
                    ) from err

            serialized_inputs["aux_operators"].append(op.primitive.to_list())

    initial_point = kwargs.get("initial_point", None)
    serialized_inputs["initial_point"] = list(initial_point)

    use_initial_mapping = kwargs.get("use_initial_mapping", False)
    serialized_inputs["use_initial_mapping"] = use_initial_mapping

    optimizer = kwargs.get("optimizer", SPSA(maxiter=300))
    serialized_inputs["optimizer"] = {
        "__class__.__name__": optimizer.__class__.__name__,
        "__class__": str(optimizer.__class__),
        "settings": getattr(optimizer, "settings", {}),
    }

    reps = kwargs.get("reps", 1)
    serialized_inputs["reps"] = reps

    shots = kwargs.get("shots", 1024)
    serialized_inputs["shots"] = shots

    alpha = kwargs.get("alpha", 1.0)  # CVaR expectation
    serialized_inputs["alpha"] = alpha

    measurement_error_mitigation = kwargs.get("measurement_error_mitigation", False)
    serialized_inputs["measurement_error_mitigation"] = measurement_error_mitigation

    use_swap_strategies = kwargs.get("use_swap_strategies", True)
    serialized_inputs["use_swap_strategies"] = use_swap_strategies

    use_pulse_efficient = kwargs.get("use_pulse_efficient", False)
    serialized_inputs["use_pulse_efficient"] = use_pulse_efficient

    optimization_level = kwargs.get("optimization_level", 1)
    serialized_inputs["optimization_level"] = optimization_level

    # select expectation algorithm
    if alpha == 1:
        expectation = PauliExpectation()
    else:
        expectation = CVaRExpectation(alpha, PauliExpectation())

    # add measurement error mitigation if specified
    if measurement_error_mitigation:
        # allow for TensoredMeasFitter as soon as runtime runs on latest Terra
        measurement_error_mitigation_cls = TensoredMeasFitter
        measurement_error_mitigation_shots = shots
    else:
        measurement_error_mitigation_cls = None
        measurement_error_mitigation_shots = None

    # Define the transpiler passes to use.
    pass_manager = None
    if use_swap_strategies:
        pass_manager = swap_pass_manager_creator(
            backend, use_initial_mapping=use_initial_mapping
        )

    pulse_passes = pulse_pass_creator(backend) if use_pulse_efficient else None

    # set up quantum instance
    quantum_instance = QuantumInstance(
        backend,
        shots=shots,
        measurement_error_mitigation_shots=measurement_error_mitigation_shots,
        measurement_error_mitigation_cls=measurement_error_mitigation_cls,
        pass_manager=pass_manager,
        bound_pass_manager=pulse_passes,
        optimization_level=optimization_level,
    )

    quantum_instance.circuit_summary = True

    # publisher for user-server communication
    publisher = Publisher(user_messenger)

    # dictionary to store the history of the optimization
    history = {"nfevs": [], "params": [], "energy": [], "std": []}

    def store_history_and_forward(nfevs, params, energy, std):
        # store information
        history["nfevs"].append(nfevs)
        history["params"].append(params)
        history["energy"].append(energy)
        history["std"].append(std)

        # and forward information to users callback
        publisher.callback(nfevs, params, energy, std)

    # construct the QAOA instance
    qaoa = VQE(
        ansatz=QAOAAnsatz(operator, reps),
        optimizer=optimizer,
        initial_point=initial_point,
        expectation=expectation,
        callback=store_history_and_forward,
        quantum_instance=quantum_instance,
    )
    result = qaoa.compute_minimum_eigenvalue(operator, aux_operators)

    serialized_result = {
        "optimizer_time": result.optimizer_time,
        "optimal_value": result.optimal_value,
        "optimal_point": result.optimal_point,
        "optimal_parameters": None,  # ParameterVectorElement is not serializable
        "cost_function_evals": result.cost_function_evals,
        "eigenstate": result.eigenstate,
        "eigenvalue": result.eigenvalue,
        "aux_operator_eigenvalues": result.aux_operator_eigenvalues,
        "optimizer_history": history,
        "inputs": serialized_inputs,
    }

    return serialized_result
