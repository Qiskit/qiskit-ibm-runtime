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

"""
Pass to convert the :class:`qiskit.circuit.gate.Gate`s of a circuit to a Clifford gate.
"""

from typing import Callable, List, Optional, Tuple, Type
from copy import deepcopy
import numpy as np

from qiskit.circuit import Instruction
from qiskit.circuit.gate import Gate
from qiskit.circuit.library import CXGate, CZGate, ECRGate, IGate, RZGate, SXGate, XGate
from qiskit.exceptions import QiskitError
from qiskit.quantum_info import Clifford
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

ISA_SUPPORTED_GATES = (CXGate, CZGate, ECRGate, IGate, RZGate, SXGate, XGate)
"""The set of gates that can be found in an ISA circuit."""


def _is_clifford(instruction: Instruction) -> bool:
    r"""
    Checks if an instruction is a valid Clifford gate by trying to cast it as a Clifford object.
    """
    try:
        Clifford(instruction)
    except QiskitError:
        return False
    return True


class ToClifford(TransformationPass):
    """
    Convert the :class:`qiskit.circuit.gate.Gate`s of a circuit to a Clifford gate.

    This pass is optimized to run efficiently on ISA circuits, which contain only Clifford gates
    from a restricted set or :class:`qiskit.circuit.library.RZGate`s by arbitrary angles.
    If applied to ISA circuits, it skips all the Clifford gates, while it rounds the angle
    of every :class:`qiskit.circuit.library.RZGate` to the closest multiple of `pi/2` .

    .. code-block:: python

        import numpy as np

        from qiskit import QuantumCircuit
        from qiskit.transpiler import PassManager
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

        from qiskit_ibm_runtime.fake_provider import FakeKyiv
        from qiskit_ibm_runtime.transpiler.passes import ToClifford

        # An ISA circuit ending with a Z rotation by pi/3
        qc = QuantumCircuit(2)
        qc.sx(0)
        qc.rz(np.pi/2, 0)
        qc.sx(0)
        qc.cx(0, 1)
        qc.rz(np.pi/3, 0)  # non-Clifford rotation

        # Turn into a Clifford circuit that ends with a rotation by pi/2
        pm = PassManager([ToClifford()])
        clifford_qc = pm.run(qc)

    This pass can also be applied to circuits that contain non-ISA gates, albeit at the cost of
    additional validation logic that may result in reduced performance. In this case, it skips all
    the Clifford gates in the circuit, and it replaces the non-Clifford gates as specified by the
    given ``rules``.

    .. code-block:: python

        import numpy as np

        from qiskit import QuantumCircuit
        from qiskit.circuit.library import RZGate, RXGate, HGate
        from qiskit.transpiler import PassManager
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

        from qiskit_ibm_runtime.fake_provider import FakeKyiv
        from qiskit_ibm_runtime.transpiler.passes import ToClifford

        # An non-ISA circuit ending with a Z rotation by pi/3
        qc = QuantumCircuit(2)
        qc.h(0)  # non-ISA Clifford gate
        qc.cx(0, 1)
        qc.rx(np.pi/3, 0)  # non-ISA non-Clifford rotation
        qc.rz(np.pi/3, 0)  # ISA non-Clifford rotation

        # A set of rules to replace every non-Clifford X rotation with a rotation
        # by `pi`, and every non-Clifford Z rotation with a rotation by `pi/2`.
        rules = [
            (RXGate, lambda x: RXGate(np.pi)),
            (RZGate, lambda x: RZGate(0)),
        ]

        # Turn `qc` into a Clifford circuit
        # The pass skips `h` and `cx` since they are Cliffords, and it replaces
        # `rx` and `rz` as dictated by the rules.
        pm = PassManager([ToClifford(rules)])
        clifford_qc = pm.run(qc)

    Args:
        rules: A list of tuples of the form ``(type, fn)``, where ``type`` is gate type and
            ``fn`` is a function that specifies how non-Clifford gates of the given type
            should be replaced. If this list contains Clifford types (e.g., ``HGate``), these
            are simply ignored.
    Raises:
        ValueError: If the given circuit contains non-Clifford gates for which rules are missing.
        ValueError: If a rule is invalid, meaning that it leads to replacing a gate with a
            non-Clifford gate.
    """

    def __init__(self, rules: Optional[List[Tuple[Type[Gate], Callable]]] = None):
        super().__init__()

        self._rules = rules or []
        self._types_with_custom_rules = tuple(rule[0] for rule in self.rules)
        self._types_with_default_rules = deepcopy(ISA_SUPPORTED_GATES)

        # If user specified a custom rule for RZGate, remove RZGate from default rules.
        if RZGate in self._types_with_custom_rules:
            self._types_with_default_rules = tuple(
                t for t in self._types_with_default_rules if t != RZGate
            )  # type: ignore

    @property
    def rules(self) -> List[Tuple[Type[Gate], Callable]]:
        r"""
        A list of replacement rules for non-ISA non-Clifford gates.
        """
        return self._rules

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        for node in dag.op_nodes():
            if isinstance(node.op, self._types_with_default_rules):
                # Fast handling of ISA gates. It rounds the angle of `RZ`s to the nearest
                # multiple of pi/2, while skipping every other gate.
                if isinstance(node.op, RZGate):
                    angle = node.op.params[0]
                    rem = angle % (np.pi / 2)
                    new_angle = angle - rem if rem < np.pi / 4 else angle + np.pi / 2 - rem
                    dag.substitute_node(node, RZGate(new_angle), inplace=True)
            else:
                # Handle non-ISA gates, which may be either Clifford or non-Clifford (requires
                # rule).
                if _is_clifford(node.op):
                    dag.substitute_node(node, node.op, inplace=True)
                else:
                    if self._types_with_custom_rules and isinstance(
                        node.op, self._types_with_custom_rules
                    ):
                        # If there is a rule for the given gate, apply it
                        idx = self._types_with_custom_rules.index(node.op.__class__)
                        fn = self.rules[idx][1]
                        new_op = fn(node.op)

                        # verify that the new gate is indeed Clifford
                        if _is_clifford(new_op):
                            dag.substitute_node(node, new_op, inplace=True)
                        else:
                            raise ValueError(f"Invalid rule for ``{node.op.__class__.__name__}``.")
                    else:
                        raise ValueError(f"Missing rule for ``{node.op.__class__.__name__}``.")
        return dag
