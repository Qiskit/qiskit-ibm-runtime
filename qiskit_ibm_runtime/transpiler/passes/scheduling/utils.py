# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utility functions for scheduling passes."""

from __future__ import annotations

from collections.abc import Callable, Generator
from functools import lru_cache
from typing import TypeAlias

from qiskit.circuit import ControlFlowOp, Measure, Parameter, Reset
from qiskit.dagcircuit import DAGCircuit, DAGOpNode

BlockOrderingCallableType = Callable[[DAGCircuit], Generator[DAGOpNode, None, None]]


def block_order_op_nodes(dag: DAGCircuit) -> Generator[DAGOpNode, None, None]:
    """Yield nodes such that they are sorted into groups of blocks that minimize synchronization.

    Measurements are also grouped.
    """

    def _is_grouped_measure(node: DAGOpNode) -> bool:
        """Does this node need to be grouped?"""
        return isinstance(node.op, (Reset, Measure))

    def _is_block_trigger(node: DAGOpNode) -> bool:
        """Does this node trigger the end of a block?"""
        return isinstance(node.op, ControlFlowOp)

    @lru_cache(maxsize=8192)
    def _emit(
        node: DAGOpNode,
        grouped_measure: tuple[DAGOpNode],
        block_triggers: tuple[DAGOpNode],
    ) -> bool:
        """Should we emit this node?"""
        for measure in grouped_measure:
            if dag.is_predecessor(node, measure):
                return True
        for block_trigger in block_triggers:
            if dag.is_predecessor(node, block_trigger):
                return True

        return _is_grouped_measure(node) or _is_block_trigger(node)

    # Begin processing nodes in order
    next_nodes = dag.topological_op_nodes()
    while next_nodes:
        curr_nodes = next_nodes  # Setup the next iteration nodes
        next_nodes_set = set()  # Nodes that will make it into the next iteration
        next_nodes = []  # Nodes to process in order in the next iteration
        to_push = []  # Do we push this to the very last block?
        yield_measures = []  # Measures/resets we will yield first
        yield_block_triggers = []  # Followed by block triggers (conditionals)
        block_break = False  # Did we encounter a block trigger in this iteration?
        for node in curr_nodes:
            # If we have added this node to the next set of nodes
            # skip for now.
            if node in next_nodes_set:
                next_nodes.append(node)
                continue

            # If this nodes is a measurement
            # push on the measurements to process
            if _is_grouped_measure(node):
                block_break = True
                node_descendants = dag.descendants(node)
                next_nodes_set |= set(node_descendants)
                yield_measures.append(node)
            # If this node is a block push this onto
            # the block trigger list.
            elif _is_block_trigger(node):
                block_break = True
                node_descendants = dag.descendants(node)
                next_nodes_set |= set(node_descendants)
                yield_block_triggers.append(node)
            # Otherwise we push onto the final list of blocks to emit
            # as part of the final block.
            else:
                to_push.append(node)

        new_to_push = []
        for node in to_push:
            node_descendants = dag.descendants(node)
            if any(
                _emit(descendant, tuple(yield_measures), tuple(yield_block_triggers))
                for descendant in node_descendants
                if isinstance(descendant, DAGOpNode)
            ):
                yield node
            else:
                new_to_push.append(node)

        to_push = new_to_push

        # First emit the measurements which will feed
        for node in yield_measures:
            yield node
        # Into the block triggers we will emit.
        for node in yield_block_triggers:
            yield node

        # We're at the last block and emit the final nodes
        if not block_break:
            for node in to_push:
                yield node
            break
        # Otherwise emit the final nodes
        # Add to the front of the list to be processed next
        to_push.extend(next_nodes)
        next_nodes = to_push

    _emit.cache_clear()


InstrKey: TypeAlias = (
    tuple[str, None, None] | tuple[str, tuple[int], None] | tuple[str, tuple[int], tuple[Parameter]]
)
