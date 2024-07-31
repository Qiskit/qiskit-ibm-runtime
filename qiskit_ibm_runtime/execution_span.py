# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Execution span classes."""

from typing import Sequence, Union, Iterable
from datetime import datetime
from dataclasses import dataclass


# The format accepted by ``numpy.ndarray.__getitem__()``.
SliceType = tuple[Union[slice, int, list[int]], ...]


@dataclass(frozen=True)  # TODO: add `slots=True` when we move to Python >= 3.10
class ExecutionSpan:
    """Stores an execution time span for a subset of job data."""

    start: datetime
    """The start time of the span, in UTC."""

    stop: datetime
    """The stop time of the span, in UTC."""

    uuid: str
    """A UUID for this execution.

    When execution spans from different pub results share a UUID, it indicates that their
    executions occurred in the same hardware batch.
    """

    data_slice: SliceType
    r"""Which data has dependence on this execution span.
    
    Data from the primitives are array-based, with every field in a 
    :class:`~PubResult`\s :class:`~.DataBin` sharing the same base shape.
    Therefore, the format of this field is the same format accepted by 
    NumPy slicing, where the value indicates which slice of each field in the
    data bin depend on raw data collected during this execution span.

    ```python
    pub_result = job.result()[0]
    data = pub_result.data

    # this is the subset of data collected during this span
    span_data = data.my_field[execution_span.data_slice]
    ```
    """


class ExecutionSpanCollection(Sequence[ExecutionSpan]):
    """A collection of timings for the PUB result."""

    def __init__(self, spans: Iterable[ExecutionSpan]):
        self._spans = spans

    def __len__(self):
        pass

    def __getitem__(self, index):
        pass

    @property
    def start(self) -> datetime:
        """The start time of the entire collection, in UTC."""
        return min(span.start for span in self)

    @property
    def stop(self) -> datetime:
        """The stop time of the entire collection, in UTC."""
        return max(span.stop for span in self)

    def plot(self):
        """Show a timing diagram"""
        pass
